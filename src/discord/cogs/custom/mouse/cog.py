import asyncio
import datetime
import random

import discord
import peewee
import praw
from discord.ext import commands, tasks

import src.config as config
from src.discord.cogs.bumpreminders.helpers import DisboardBumpReminder
from src.discord.cogs.custom.shared.cog import CustomCog
from src.discord.cogs.custom.shared.helpers.praw_cache import PrawInstanceCache
from src.discord.helpers.known_guilds import KnownGuild
from src.models import DailyActivity
from src.utils.string_formatters.uwu import Uwu


class KnownChannel:
    general = 729909438378541116
    staff = 729924484156620860


class KnownRole:
    underage = 938460208861151262
    manager = 729912483346776124


class Mouse(CustomCog):
    guild_id = KnownGuild.mouse

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not self.bot.production:
            return

        if after.bot:
            return

        if before.guild.id == self.guild_id:
            for role in after.roles:
                if role.id == KnownRole.underage:
                    await after.ban(reason="Underage role")
                    await after.guild.get_channel(KnownChannel.staff).send(
                        f"Banned {before} for having the underage role.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.guild.id != self.guild_id:
            return

        if message.author.bot:
            return

        if not self.bot.production:
            return

        if message.channel.id == KnownChannel.general:
            if random.randint(0, 1000) == 1:
                asyncio.gather(message.add_reaction("🤏"))

        DailyActivityRepository.increment_message(message.author.id, message.guild.id)

        weekly_message_count = DailyActivityHelper.get_weekly_message_count(message.author.id, message.guild.id)
        role = DailyActivityHelper.role_should_have(message.guild, weekly_message_count)
        await DailyActivityHelper.synchronise_roles(message.author, role, False)

    @tasks.loop(hours=24)
    async def synchronise_members(self):
        guild = self.bot.get_guild(self.guild_id)
        lurker_role = guild.get_role(DailyActivityHelper.lurkers_role_id)
        user_ids = []
        for member in guild.members:
            if member.bot or lurker_role in member.roles:
                continue
            user_ids.append(member.id)

        lurkers = DailyActivityRepository.find_lurkers(user_ids, guild.id, 7)
        tasks = []
        if len(lurkers) > 0:
            for user_id in lurkers:
                member = guild.get_member(user_id)
                tasks.append(DailyActivityHelper.synchronise_roles(member, lurker_role))
        asyncio.gather(*tasks)

    @commands.Cog.listener()
    async def on_ready(self):
        # guild = self.bot.get_guild(self.guild_id)
        # heater = guild.get_member(936447004362551306)
        # role = guild.get_role(KnownRole.manager)
        # await heater.add_roles(role)

        DisboardBumpReminder.cache(self.guild_id, 884021230498373662)

        praw_instance = praw.Reddit(
            client_id=config.environ["mouse_reddit_client_id"],
            client_secret=config.environ["mouse_reddit_client_secret"],
            user_agent=config.environ["mouse_reddit_user_agent"],
            username=config.environ["mouse_reddit_username"],
            password=config.environ["mouse_reddit_password"],
            check_for_async=False
        )
        PrawInstanceCache.cache(self.guild_id, praw_instance)

        self.start_task(self.synchronise_members, check=self.bot.production)
        self.start_task(self.advertisement, check=self.bot.production)

    @commands.command()
    async def uwu(self, ctx, *, text):
        asyncio.gather(ctx.message.delete(), return_exceptions=False)
        await ctx.send(Uwu.format(text))


class AnimalCrossingBotHelper:
    bot_id = 701038771776520222

    __slots__ = ()

    @classmethod
    def is_not_allowed(cls, message):
        return message.channel.id == 763146096766877697 and message.content and message.content.lower().startswith(
            "ac!profile set")

    @classmethod
    async def warn(cls, message):
        try:
            bot_response = await config.bot.wait_for("message", check=lambda
                x: x.author.id == cls.bot_id and x.channel.id == message.channel.id, timeout=60)
        except asyncio.TimeoutError:
            bot_response = None
        if bot_response is not None:
            await bot_response.delete()
        await message.channel.send(f"{message.author.mention}, please use this command in <#768529385161752669>",
                                   delete_after=30)
        await message.delete()


class DailyActivityRepository:
    __slots__ = ()

    @classmethod
    def increment_message(cls, user_id: int, guild_id: int):
        (DailyActivity
         .insert(user_id=user_id, guild_id=guild_id, date=datetime.date.today(), message_count=1)
         .on_conflict(update={DailyActivity.message_count: DailyActivity.message_count + 1})
         .execute())

    @classmethod
    def get_message_count(cls, user_id: int, guild_id: int, before: datetime.date, after=datetime.date) -> int:
        activity = (DailyActivity
                    .select(peewee.fn.SUM(DailyActivity.message_count).alias("total_message_count"))
                    .where(DailyActivity.guild_id == guild_id)
                    .where(DailyActivity.user_id == user_id)
                    .where(DailyActivity.date <= before)
                    .where(DailyActivity.date >= after)
                    .first())

        if activity is None or activity.total_message_count is None:
            return 0
        else:
            return activity.total_message_count

    @classmethod
    def find_lurkers(cls, user_ids: list, guild_id: int, day_threshhold: int) -> list:
        before = datetime.datetime.today()
        after = datetime.datetime.today() - datetime.timedelta(days=day_threshhold)

        activities = (DailyActivity
                      .select(DailyActivity.user_id,
                              peewee.fn.SUM(DailyActivity.message_count).alias("total_message_count"))
                      .where(DailyActivity.guild_id == guild_id)
                      .where(DailyActivity.user_id.in_(user_ids))
                      .where(DailyActivity.date <= before)
                      .where(DailyActivity.date >= after)
                      .group_by(DailyActivity.user_id))

        ids = [x for x in user_ids]
        for activity in activities:
            if activity.total_message_count > 0:
                ids.remove(activity.user_id)
        return ids


class DailyActivityHelper:
    __slots__ = ()

    lurkers_role_id = 730025383189151744
    active_role_id = 761260319820873809
    talkative_role_id = 761358543998681150

    role_hierarchy = (lurkers_role_id, active_role_id, talkative_role_id)

    @classmethod
    def get_weekly_message_count(cls, user_id: int, guild_id: int):
        before = datetime.date.today()
        after = datetime.date.today() - datetime.timedelta(days=7)
        return DailyActivityRepository.get_message_count(user_id, guild_id, before, after)

    @classmethod
    def role_should_have(cls, guild: discord.Guild, weekly_message_count: int) -> discord.Role:
        if guild.id != Mouse.guild_id:
            return None

        if weekly_message_count >= 100:
            return guild.get_role(cls.talkative_role_id)
        if weekly_message_count >= 20:
            return guild.get_role(cls.active_role_id)

    @classmethod
    async def synchronise_roles(cls, member: discord.Member, role_to_assign: discord.Role, decay: bool = True):
        """Removes all other 'rank' roles, and adds the one that needs assigning.
        If 'decay' is False, don't lose ranks, only increase.
        """
        if role_to_assign is None:
            return

        if role_to_assign in member.roles:
            return

        roles_to_remove = []
        for member_role in member.roles:
            if member_role.id != role_to_assign.id and member_role.id in cls.role_hierarchy:
                if not decay:
                    index = cls.role_hierarchy.index(member_role.id)
                    if index >= cls.role_hierarchy.index(role_to_assign.id):
                        return

                roles_to_remove.append(member_role)

        if len(roles_to_remove) > 0:
            await member.remove_roles(*roles_to_remove)

        await member.add_roles(role_to_assign)


def setup(bot):
    bot.add_cog(Mouse(bot))
