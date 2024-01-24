import asyncio
import datetime
import random

import discord
from discord.ext import commands

import src.config as config
from src.constants import Constants, BR
from src.disc.cogs.core import BaseCog
from src.disc.errors.base import SendableException
from src.models import Conversant, Participant, Conversation


class NotAvailable(Exception): pass


user_ids_currently_being_checked = []


async def check_if_available(user):
    if user.id in user_ids_currently_being_checked:
        return False

    user_ids_currently_being_checked.append(user.id)

    def check(message):
        if message.author.id != user.id:
            return False
        if not isinstance(message.channel, discord.DMChannel):
            return False
        if message.content.lower() in ("no", "n"):
            raise NotAvailable()
        if message.content.lower() in ("yes", "y"):
            return True
        return False

    timeout = 60

    try:
        await user.send("Are you available to talk? (yes | no)", delete_after=timeout)
    except discord.errors.Forbidden:
        return False

    available = False
    try:
        await config.bot.wait_for("message", check=check, timeout=timeout)
        available = True
    except asyncio.TimeoutError:
        pass
    except NotAvailable:
        pass

    user_ids_currently_being_checked.remove(user.id)
    return available


def is_command(message):
    bot = config.bot
    prefix = bot.command_prefix
    prefixes = []
    if isinstance(prefix, str):
        prefixes.append(prefix)
    elif isinstance(prefix, list):
        prefixes = prefix

    for prefix in prefixes:
        if message.content.startswith(prefix):
            return True
    return False


class ConversationsCog(BaseCog, name="Conversations"):
    cached_conversations = {}

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        query = Conversation.select().where(Conversation.finished == False)
        for conversation in query:
            self.cached_conversations[conversation.participant1.user_id] = conversation
            self.cached_conversations[conversation.participant2.user_id] = conversation

    @commands.Cog.listener()
    async def on_message(self, message):
        if len(self.cached_conversations) == 0:
            return
        if not self.bot.production:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return
        if is_command(message):
            return
        try:
            conversation = self.get_conversation(message.author)
        except:
            return

        other = conversation.get_other(message.author)
        await other.send(message.content)

    def get_conversation(self, user):
        try:
            return self.cached_conversations[user.id]
        except KeyError:
            raise SendableException(self.bot.translate("no_running_conversation"))

    @commands.group()
    @commands.dm_only()
    async def conversation(self, ctx):
        if not self.bot.production:
            raise SendableException(ctx.translate("wrong_prefix"))

    @conversation.command(name="reveal")
    async def conversation_reveal(self, ctx):
        """Invite the other person to reveal eachother.
           You'll need to have been in a conversation for at least 30 minutes to be able to do this.
        """
        conversation = self.get_conversation(ctx.author)

        if conversation.duration.minutes < 30:
            raise SendableException(ctx.translate("conversation_too_short"))

        for participant in conversation.get_participants():
            if participant.conversant.user_id == ctx.author.id:
                other = conversation.get_other(participant)
                participant.reveal = True
                participant.save()
                if other.reveal:
                    await conversation.reveal()
                else:
                    lines = []
                    lines.append("The other person invited you to reveal eachother.")
                    lines.append(f"To accept type '{ctx.prefix}conversation reveal'")
                    await other.send("\n".join(lines))
                break

    @conversation.command(name="toggle", aliases=["enable", "disable"])
    async def conversation_toggle(self, ctx):
        conversant, _ = Conversant.get_or_create(user_id=ctx.author.id)
        values = {"enable": True, "disable": False, "toggle": not conversant.enabled}
        conversant.enabled = values[ctx.invoked_with]
        conversant.save()
        await ctx.success(ctx.translate("conversations_toggled_" + ("on" if conversant.enabled else "off")))

    @conversation.command(name="end")
    async def conversation_end(self, ctx):
        """Ends the currently active conversation."""
        conversation = self.get_conversation(ctx.author)

        conversation.end_time = datetime.datetime.utcnow()
        conversation.finished = True
        conversation.save()

        for user_id in conversation.get_user_ids():
            user = self.bot.get_user(user_id)
            try:
                del self.cached_conversations[user.id]
            except:
                pass
            finally:
                await user.send(ctx.translate("conversation_ended"))

    @conversation.command(name="start")
    async def conversation_start(self, ctx):
        if ctx.author.id in self.cached_conversations:
            raise SendableException(ctx.translate("already_running_conversation"))

        conversant, _ = Conversant.get_or_create(user_id=ctx.author.id)
        if not conversant.enabled:
            conversant.enabled = True
            conversant.save()

        user_ids = []
        user_ids_in_conversation = list(self.cached_conversations.keys())
        for cs in Conversant.get_available(user_ids_in_conversation):
            if cs.user_id != ctx.author.id:
                user_ids.append(cs.user_id)

        if len(user_ids) == 0:
            raise SendableException(ctx.translate("no_conversants_available"))

        await ctx.success(ctx.translate("attempting_to_find_conversant"))

        random.shuffle(user_ids)

        user_to_speak_to = None
        for user_id in user_ids:
            user = self.bot.get_user(user_id)
            if user is None:
                continue
            if await check_if_available(user):
                user_to_speak_to = user
                break
            else:
                await ctx.send(ctx.translate("still_looking_please_be_patient"))

        if user_to_speak_to is None:
            raise SendableException(ctx.translate("no_conversants_available"))

        conversation = Conversation()
        conversation.participant1 = Participant.create(conversant=conversant)
        conversation.participant2 = Participant.create(conversant=Conversant.get(user_id=user_to_speak_to.id))
        conversation.save()

        embed = get_conversation_tutorial_embed(ctx)
        for participant in conversation.get_participants():
            other = conversation.get_other(participant)
            embed.set_footer(text=f"Speaking to conversant with id '{other.key}'")
            await participant.send(embed=embed)
            self.cached_conversations[participant.conversant.user_id] = conversation


def command_to_field(ctx, command, description):
    kwargs = {}
    kwargs["name"] = description
    kwargs["value"] = f"`{ctx.prefix}{command.qualified_name}`\n{command.callback.__doc__}{BR}"
    kwargs["inline"] = False
    return kwargs


def get_conversation_tutorial_embed(ctx):
    embed = discord.Embed(color=ctx.guild_color)
    lines = []
    lines.append("Conversation has been started with an anonymous person.")
    lines.append("Chat by chatting in DMs (commands will not work)")
    lines.append(BR)

    end_command = ctx.bot.get_command("conversation end")
    embed.add_field(**command_to_field(ctx, end_command, "⛔ Ending a conversation"))

    reveal_command = ctx.bot.get_command("conversation reveal")
    embed.add_field(**command_to_field(ctx, reveal_command, "🥷 Revealing eachother"))

    embed.description = "\n".join(lines)
    return embed


async def setup(bot):
    await bot.add_cog(ConversationsCog(bot))
