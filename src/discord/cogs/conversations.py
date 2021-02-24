import asyncio
import datetime
import random

import discord
from discord.ext import commands

import src.config as config
import src.discord.helpers.pretty as pretty
from src.models import Conversant, Participant, Conversation, database
from src.discord.errors.base import SendableException
from src.discord.cogs.core import BaseCog

class NotAvailable(Exception): pass

async def check_if_available(user):
    def check(message):
        if message.author.id != user.id:
            return False
        if not isinstance(message.channel, discord.DMChannel):
            return False
        if message.content.lower() in ("no", "n"):
            raise NotAvailable()
        if message.content.lower() in ("yes", "y"):
            return True
        return True

    await user.send("Are you available to talk? (yes | no)")
    try:
        await config.bot.wait_for("message", check = check, timeout = 60)
        return True
    except asyncio.TimeoutError:
        await user.send("You are clearly not available to talk.")
        return False
    except NotAvailable:
        return False

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

class ConversationsCog(BaseCog, name = "Conversations"):
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
        if message.author.id not in self.cached_conversations:
            return

        conversation = self.cached_conversations[message.author.id]
        other = conversation.get_other(message.author)
        await other.send(message.content)

    @commands.group()
    @commands.dm_only()
    async def conversation(self, ctx):
        pass

    @conversation.command(name = "reveal")
    async def conversation_reveal(self, ctx):
        if ctx.author.id not in self.cached_conversations:
            raise SendableException(ctx.translate("no_running_conversation"))

        conversation = self.cached_conversations[ctx.author.id]

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

    @conversation.command(name = "toggle", aliases = ["enable", "disable"])
    async def conversation_toggle(self, ctx):
        conversant, _ = Conversant.get_or_create(user_id = ctx.author.id)
        values = {"enable": True, "disable": False, "toggle": not conversant.enabled}
        conversant.enabled = values[ctx.invoked_with]
        conversant.save()
        await ctx.success(ctx.translate("conversations_toggled_" + ("on" if conversant.enabled else "off")))

    @conversation.command(name = "end")
    async def conversation_end(self, ctx):
        if ctx.author.id not in self.cached_conversations:
            raise SendableException(ctx.translate("no_running_conversation"))

        conversation = self.cached_conversations[ctx.author.id]
        conversation.end_time = datetime.datetime.utcnow()
        conversation.finished = True
        conversation.save()

        for user_id in conversation.get_user_ids():
            user = self.bot.get_user(user_id)
            del self.cached_conversations[user.id]
            await user.send(ctx.translate("conversation_ended"))

    @conversation.command(name = "start")
    async def conversation_start(self, ctx):
        if ctx.author.id in self.cached_conversations:
            raise SendableException(ctx.translate("already_running_conversation"))

        conversant, _ = Conversant.get_or_create(user_id = ctx.author.id)
        conversant.enabled = True
        conversant.save()

        user_ids = []
        user_ids_in_conversation = list(self.cached_conversations.items())
        for conversant in Conversant.get_available(user_ids_in_conversation):
            if conversant.user_id != ctx.author.id:
                user_ids.append(conversant.user_id)

        if len(user_ids) == 0:
            raise SendableException(ctx.translate("no_conversants_available"))

        await ctx.success(ctx.translate("attempting_to_find_conversant"))

        random.shuffle(user_ids)

        user_to_speak_to = None
        for user_id in user_ids:
            user = self.bot.get_user(user_id)
            if await check_if_available(user):
                user_to_speak_to = user
                break

        if user_to_speak_to is None:
            raise SendableException(ctx.translate("no_conversants_available"))

        conversation = Conversation()
        conversation.participant1 = Participant.create(conversant = conversant)
        conversation.participant2 = Participant.create(conversant = Conversant.get(user_id = user_to_speak_to.id))
        conversation.save()

        embed = discord.Embed()
        lines = []
        lines.append("Conversation has been started with an anonymous person.")
        lines.append("Chat by chatting in DMs (commands will not work)")
        lines.append(f"To end use '{ctx.prefix}conversation end'")

        embed.description = "\n".join(lines)

        for participant in conversation.get_participants():
            other = conversation.get_other(participant)
            embed.set_footer(text = f"Speaking to conversant with id '{other.key}'")
            await participant.send(embed = embed)
            self.cached_conversations[participant.conversant.user_id] = conversation

def setup(bot):
    bot.add_cog(ConversationsCog(bot))