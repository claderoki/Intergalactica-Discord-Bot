import asyncio
import datetime
import random

import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands, tasks

from src.discord.cogs.core import BaseCog
from src.discord.cogs.custom.shared.helpers.helpers import ChannelHelper
from src.discord.cogs.custom.shared.helpers.simple_poll import SimplePoll
from src.discord.errors.base import SendableException
from src.discord.helpers.known_guilds import KnownGuild
from src.models import (TemporaryVoiceChannel, TemporaryTextChannel, database)


class Intergalactica(BaseCog):
    _welcome_message_configs = {}

    last_member_join = None

    _role_ids = {
        "selfies": 748566253534445568,
        "vc_access": 761599311967420418,
        "5k+": 778744417322139689,
    }

    _channel_ids = {
        "general": 744650481682481233,
        "roles": 742303560988885044,
        "welcome": 742187165659693076,
        "selfies": 744703465086779393,
        "staff_votes": 863775839945621534,
        "staff_chat": 863774968848449546,
        "introductions": 742567349613232249,
        "c3po-log": 863775783940390912,
    }

    def get_channel(self, name):
        return self.bot.get_channel(self._channel_ids[name])

    def __init__(self, bot):
        super().__init__(bot)
        self.welcome_messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        SimplePoll.add_guild_data(KnownGuild.intergalactica, self._channel_ids["staff_votes"],
                                  self._channel_ids["staff_chat"])

        self.start_task(self.illegal_member_purger, check=self.bot.production)
        self.start_task(self.introduction_purger, check=self.bot.production)
        self.start_task(self.temp_vc_poller, check=self.bot.production)
        self.start_task(self.mouse_role_cleanup, check=self.bot.production)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if SimplePoll.is_eligible(payload):
            poll = await SimplePoll.from_payload(payload)
            if poll.should_finish():
                poll.finish()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        if not self.bot.production:
            return

        guild_data = SimplePoll.guild_data.get(message.guild.id)
        if guild_data is not None and guild_data["vote_channel"] == message.channel.id:
            coros = [message.add_reaction(x) for x in SimplePoll.options]
            asyncio.gather(*coros)
            return

        if message.guild.id != KnownGuild.intergalactica:
            return

        if message.channel.id == self._channel_ids["general"]:
            if self.last_member_join is not None and "welcome" in message.content.lower():
                time_here = relativedelta(datetime.datetime.utcnow(), self.last_member_join)
                if time_here.minutes <= 5:
                    emoji = random.choice(("💛", "🧡", "🤍", "💙", "🖤", "💜", "💚", "❤️"))
                    asyncio.gather(message.add_reaction(emoji))

    async def log(self, channel_name, content=None, **kwargs):
        channel = self.get_channel(channel_name)
        await channel.send(content=content, **kwargs)

    @commands.command(name="vcchannel")
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
        channel = await category.create_voice_channel(name or "Temporary voice channel",
                                                      reason=f"Requested by {ctx.author}")
        TemporaryVoiceChannel.create(guild_id=ctx.guild.id, channel_id=channel.id)
        await ctx.success()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.production:
            return

        if member.guild.id == KnownGuild.intergalactica:
            welcome_channel = self.get_channel("welcome")
            text = self.bot.translate("member_join")

            embed = discord.Embed(color=self.bot.get_dominant_color(member.guild))
            embed.description = text.format(member=member)

            asyncio.gather(welcome_channel.send(embed=embed))

            self.last_member_join = datetime.datetime.utcnow()
            text = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
            message = await self.get_channel("general").send(text)
            self.welcome_messages[member.id] = message

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.production:
            return

        if member.guild.id != KnownGuild.intergalactica:
            return

        try:
            await self.welcome_messages[member.id].delete()
        except:
            pass

        welcome_channel = self.get_channel("welcome")
        text = self.bot.translate("member_leave")

        embed = discord.Embed(color=self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member=member)

        asyncio.gather(welcome_channel.send(embed=embed))

    @tasks.loop(hours=1)
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

    @tasks.loop(minutes=20)
    async def introduction_purger(self):
        channels = []
        channels.append(self.bot.get_channel(729909501578182747))
        channels.append(self.bot.get_channel(841049839466053693))

        for channel in channels:
            await ChannelHelper.cleanup_channel(channel)

    @tasks.loop(hours=5)
    async def mouse_role_cleanup(self):
        guild = self.bot.get_guild(KnownGuild.mouse)
        new_role = guild.get_role(764586989466943549)

        for member in guild.members:
            time_here = relativedelta(discord.utils.utcnow(), member.joined_at)
            more_than_week = time_here.weeks >= 1 or time_here.months > 1 or time_here.years >= 1
            if more_than_week and new_role in member.roles:
                await member.remove_roles(new_role)

    @tasks.loop(hours=1)
    async def illegal_member_purger(self):
        for guild in self.bot.guilds:
            if guild.id not in (KnownGuild.mouse,):
                continue

            for member in guild.members:
                if member.bot:
                    continue

                if not MemberHelper.has_mandatory_roles(member):
                    time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
                    if time_here.hours >= 6:
                        asyncio.gather(member.kick(reason="Missing mandatory role(s)"))


class MemberHelper:
    __slots__ = ()

    @classmethod
    def _has_mandatory_roles_mouse(cls, member) -> bool:
        role = member.guild.get_role(729913735946305548)
        if role is None:
            return True
        return role in member.roles

    @classmethod
    def has_mandatory_roles(cls, member) -> bool:
        if member.guild.id == KnownGuild.mouse:
            return cls._has_mandatory_roles_mouse(member)
        else:
            return True


def get_category(guild: discord.Guild, id: int) -> discord.CategoryChannel:
    for category in guild.categories:
        if category.id == id:
            return category


async def setup(bot):
    await bot.add_cog(Intergalactica(bot))
