import asyncio
import datetime
import random
import re
from enum import Enum

import discord
from discord.ext import commands, tasks
from dateutil.relativedelta import relativedelta

from src.discord.cogs.custom.shared.helpers.helpers import ChannelHelper
from src.discord.helpers.known_guilds import KnownGuild
import src.config as config
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers.checks import specific_guild_only
from src.discord.helpers.utility import get_context_embed
from src.models import (Earthling, Human, Item,
                        TemporaryVoiceChannel, TemporaryTextChannel, database)
from src.discord.cogs.custom.shared.helpers.simple_poll import SimplePoll

class MaliciousAction(Enum):
    blacklisted_word = 1
    invite_url       = 2
    spam             = 3

    @property
    def ban_reason(self):
        if self == self.blacklisted_word:
            return "Using blacklisted word(s)"
        elif self == self.invite_url:
            return "Advertising"
        elif self == self.spam:
            return "Spam"

async def on_malicious_action(action : MaliciousAction, member : discord.Member, **kwargs):
    ban_if_new = False

    if action == MaliciousAction.blacklisted_word:
        message = kwargs["message"]
        words = kwargs["words"]

        embed = await get_context_embed(message, amount = 5)
        embed.color = discord.Color.red()
        embed.set_author(name = f"Blacklisted word(s) used by {member} ({member.id})", url = message.jump_url)

        lines = []
        lines.append(f"The following blacklisted word(s) were used")
        lines.append(", ".join([f"**{x}**" for x in words]))
        embed.description = "{}\n{}".format("\n".join(lines), embed.description)

        sendable = member.guild.get_channel(Intergalactica._channel_ids["c3po-log"])
        asyncio.gather(sendable.send(embed = embed))

        ban_if_new = True
    elif action == MaliciousAction.invite_url:
        try:
            await kwargs["message"].delete()
        except: pass
        ban_if_new = True
    elif action == MaliciousAction.spam:
        pass

class Intergalactica(BaseCog):
    last_member_join = None

    _role_ids = {
        "selfies"   : 748566253534445568,
        "admin"     : 742243945693708381,
        "vc_access" : 761599311967420418,
        "5k+"       : 778744417322139689,
        "bumper"    : 780001849335742476,
        "age"       : {"18-20": 748606669902053387, "21-24": 748606823229030500, "25-29": 748606893387153448, "30+": 748606902363095206},
        "gender"    : {"male": 742301620062388226, "female": 742301646004027472, "other" : 742301672918745141},
        "ranks"     : {
            "luna"      : 748494880229163021,
            "nova"      : 748494888844132442,
            "aurora"    : 748494890127851521,
            "aquila"    : 748494890169794621,
            "orion"     : 748494891419697152,
            "andromeda" : 748494891751047183
        },
    }

    _channel_ids = {
        "general"        : 744650481682481233,
        "roles"          : 742303560988885044,
        "welcome"        : 742187165659693076,
        "warns"          : 777888951523606548,
        "selfies"        : 744703465086779393,
        "concerns"       : 863775516998107186,
        "staff_votes"    : 863775839945621534,
        "staff_chat"     : 863774968848449546,
        "bot_spam"       : 742163352712642600,
        "bot_commands"   : 863775558977323008,
        "introductions"  : 742567349613232249,
        "logs"           : 863775748400349214,
        "c3po-log"       : 863775783940390912,
    }

    async def get_invites(self, message):
        if "cdn" in message:
            return None

        regex = re.compile(r'discord(?:app|\.gg)/(?:invite/)?([a-zA-Z0-9\-]{2,32})')
        invite_urls = regex.findall(message)
        if len(invite_urls) == 0:
            return None

        invites = []
        for url in invite_urls:
            try:
                invite = await self.bot.fetch_invite(url)
            except discord.errors.NotFound:
                continue
            else:
                invites.append(invite)
        return invites

    def get_channel(self, name):
        return self.bot.get_channel(self._channel_ids[name])

    def __init__(self, bot):
        super().__init__(bot)
        self.welcome_messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        SimplePoll.add_guild_data(KnownGuild.intergalactica, self._channel_ids["staff_votes"], self._channel_ids["staff_chat"])

        guild = self.bot.get_guild(KnownGuild.intergalactica)

        self.start_task(self.illegal_member_purger,             check = self.bot.production)
        self.start_task(self.introduction_purger,               check = self.bot.production)
        self.start_task(self.temp_vc_poller,                    check = self.bot.production)
        self.start_task(self.mouse_role_cleanup,                check = self.bot.production)

    def on_milkyway_purchased(self, channel, member, amount):
        with database.connection_context():
            item = Item.get(code = "milky_way")
            human = self.bot.get_human(user = member)
            human.add_item(item, amount)

        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.description = f"Good job in purchasing {amount} milky way(s).\nInstructions:\n`/milkyway create` or `/milkyway extend #channel`"
        asyncio.gather(channel.send(embed = embed))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if SimplePoll.is_eligible(payload):
            poll = await SimplePoll.from_payload(payload)
            if poll.should_finish():
                poll.finish()

    def blacklisted_words_used(self, text):
        blacklisted_words = ["retard", "nigger", "fag"]

        words_used = []
        for word in blacklisted_words:
            if word in text:
                words_used.append(word)

        return words_used

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return
        if message.guild is None:
            return

        guild_data = SimplePoll.guild_data.get(message.guild.id)
        if guild_data is not None and guild_data["vote_channel"] == message.channel.id:
            coros = [message.add_reaction(x) for x in SimplePoll.options]
            asyncio.gather(*coros)
            return

        if message.guild.id != KnownGuild.intergalactica:
            return

        words = self.blacklisted_words_used(message.content.lower())
        if len(words) > 0:
            await on_malicious_action(MaliciousAction.blacklisted_word, message.author, message = message, words = words)

        invites = await self.get_invites(message.content)
        if invites:
            for invite in invites:
                if invite.guild.id != message.guild.id:
                    await on_malicious_action(MaliciousAction.invite_url, message.author, message = message)
            return

        if message.channel.id == self._channel_ids["general"]:
            if self.last_member_join is not None and "welcome" in message.content.lower():
                time_here = relativedelta(datetime.datetime.utcnow(), self.last_member_join)
                if time_here.minutes <= 5:
                    emoji = random.choice(("💛", "🧡", "🤍", "💙", "🖤", "💜", "💚", "❤️"))
                    asyncio.gather(message.add_reaction(emoji))
            elif random.randint(0, 1000) == 1:
                asyncio.gather(message.add_reaction("🤏"))

        if message.author.id == 172002275412279296: # tatsu
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                if embed.title == "Purchase Successful!":
                    field = embed.fields[0]
                    if field.name == "You Bought" and "milky way" in field.value.lower():
                        member_name = embed.footer.text.replace(" bought an item!", "")
                        class FakeCtx:
                            pass
                        ctx = FakeCtx()
                        ctx.bot = self.bot
                        ctx.guild = message.guild
                        member = await commands.MemberConverter().convert(ctx, member_name)

                        amount = int(field.value.split("`")[1])
                        self.on_milkyway_purchased(message.channel, member, amount)
                        return await message.delete()

    async def log(self, channel_name, content = None, **kwargs):
        channel = self.get_channel(channel_name)
        await channel.send(content = content, **kwargs)

    @commands.command(name = "vcchannel")
    @commands.guild_only()
    async def vc_channel(self, ctx, *args):
        name = " ".join(args) if len(args) > 0 else None

        if ctx.guild.id == KnownGuild.intergalactica:
            role = ctx.guild.get_role(self._role_ids["5k+"])
            if role not in ctx.author.roles:
                raise SendableException(f"You need the {role} role to use this command.")
            category_id = 742146159711092759
        elif ctx.guild.id == KnownGuild.cam:
            category_id = 695416318681415792
        else:
            raise SendableException("Command not available in this guild.")

        category = get_category(ctx.guild, category_id)
        channel = await category.create_voice_channel(name or "Temporary voice channel", reason = f"Requested by {ctx.author}")
        TemporaryVoiceChannel.create(guild_id = ctx.guild.id, channel_id = channel.id)
        await ctx.success()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.production:
            return

        if member.guild.id == KnownGuild.mouse:
            role    = member.guild.get_role(841072184953012275)
            general = member.guild.get_channel(729909438378541116)
            message = await general.send(f"Welcome to the server {member.mention}, {role.mention} say hello!")
            self.welcome_messages[member.id] = message
        elif member.guild.id == KnownGuild.intergalactica:
            welcome_channel = self.get_channel("welcome")
            text = self.bot.translate("member_join")

            embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
            embed.description = text.format(member = member)

            asyncio.gather(welcome_channel.send(embed = embed))

            self.last_member_join = datetime.datetime.utcnow()
            if True:
                text = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
            message = await self.get_channel("general").send(text)
            self.welcome_messages[member.id] = message

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.production:
            return

        try:
            await self.welcome_messages[member.id].delete()
        except:
            pass

        if member.guild.id != KnownGuild.intergalactica:
            return

        welcome_channel = self.get_channel("welcome")
        text = self.bot.translate("member_leave")

        embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

    @tasks.loop(hours = 1)
    async def temp_vc_poller(self):
        with database.connection_context():
            for temporary_voice_channel in TemporaryVoiceChannel:
                channel = temporary_voice_channel.channel
                if channel is None or len(channel.members) == 0:
                    query = TemporaryTextChannel.select()
                    query = query.where(TemporaryTextChannel.temp_vc == temporary_voice_channel)

                    for temporary_text_channel in query:
                        temporary_text_channel.delete_instance()
                    temporary_voice_channel.delete_instance()

    @tasks.loop(minutes = 20)
    async def introduction_purger(self):
        channels = []
        channels.append(self.bot.get_channel(729909501578182747))
        channels.append(self.bot.get_channel(841049839466053693))

        for channel in channels:
            await ChannelHelper.cleanup_channel(channel)

    @tasks.loop(hours = 5)
    async def mouse_role_cleanup(self):
        guild = self.bot.get_guild(KnownGuild.mouse)
        new_role = guild.get_role(764586989466943549)

        for member in guild.members:
            time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
            more_than_week = time_here.weeks >= 1 or time_here.months > 1 or time_here.years >= 1
            if more_than_week and new_role in member.roles:
                await member.remove_roles(new_role)

    @tasks.loop(hours = 1)
    async def illegal_member_purger(self):
        for guild in self.bot.guilds:
            if guild.id not in (KnownGuild.mouse, KnownGuild.intergalactica):
                continue

            for member in guild.members:
                if member.bot:
                    continue

                if not MemberHelper.has_mandatory_roles(member):
                    time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
                    if time_here.hours >= 6:
                        asyncio.gather(member.kick(reason = "Missing mandatory role(s)"))

class MemberHelper:
    __slots__ = ()

    @classmethod
    def _has_mandatory_roles_mouse(cls, member) -> bool:
        role = member.guild.get_role(729913735946305548)
        if role is None:
            return True
        return role in member.roles

    @classmethod
    def _has_mandatory_roles_intergalactica(cls, member) -> bool:
        return True

    @classmethod
    def has_mandatory_roles(cls, member) -> bool:
        if member.guild.id == KnownGuild.intergalactica:
            return cls._has_mandatory_roles_intergalactica(member)
        elif member.guild.id == KnownGuild.mouse:
            return cls._has_mandatory_roles_mouse(member)
        else:
            return True

def get_category(guild: discord.Guild, id: int) -> discord.CategoryChannel:
    for category in guild.categories:
        if category.id == id:
            return category

def setup(bot):
    bot.add_cog(Intergalactica(bot))
