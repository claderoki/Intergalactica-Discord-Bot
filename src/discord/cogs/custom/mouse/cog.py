import datetime
import asyncio
import discord

import peewee
from discord.ext import commands, tasks
import praw

from src.discord.cogs.custom.shared.cog import CustomCog
import src.config as config
from src.utils.string_formatters.uwu import Uwu
from src.models import DailyActivity

class Mouse(CustomCog):
    guild_id = 729843647347949638

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.guild.id != self.guild_id:
            return

        if not self.bot.production:
            return

        if message.author.bot:
            return

        DailyActivityRepository.increment_message(message.author.id, message.guild.id)

        weekly_message_count = DailyActivityHelper.get_weekly_message_count(message.author.id, message.guild.id)
        role = DailyActivityHelper.role_should_have(message.guild, weekly_message_count)
        await DailyActivityHelper.synchronise_roles(message.author, role)

    @tasks.loop(hours = 24)
    async def synchronise_members(self):
        guild = self.bot.get_guild(self.guild_id)
        for member in guild.members:
            if member.bot:
                continue
            weekly_message_count = DailyActivityHelper.get_weekly_message_count(member.id, guild.id)
            role = DailyActivityHelper.role_should_have(guild, weekly_message_count)
            await DailyActivityHelper.synchronise_roles(member, role)

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(1)
        # self.start_task(self.synchronise_members, check = True)
        await super().on_ready()
        self.praw_instances[self.guild_id] = praw.Reddit(
            client_id       = config.environ["mouse_reddit_client_id"],
            client_secret   = config.environ["mouse_reddit_client_secret"],
            user_agent      = config.environ["mouse_reddit_user_agent"],
            username        = config.environ["mouse_reddit_username"],
            password        = config.environ["mouse_reddit_password"],
            check_for_async = False
        )
 
    @commands.command()
    async def uwu(self, ctx, *, text):
        asyncio.gather(ctx.message.delete(), return_exceptions = False)
        await ctx.send(Uwu.format(text))

def setup(bot):
    bot.add_cog(Mouse(bot))

class AnimalCrossingBotHelper:
    bot_id = 701038771776520222

    __slots__ = ()

    @classmethod
    def is_not_allowed(cls, message):
        return message.channel.id == 763146096766877697 and message.content and message.content.lower().startswith("ac!profile set")

    @classmethod
    async def warn(cls, message):
        try:
            bot_response = await config.bot.wait_for("message", check = lambda x : x.author.id == cls.bot_id and x.channel.id == message.channel.id, timeout = 60)
        except asyncio.TimeoutError:
            bot_response = None
        if bot_response is not None:
            await bot_response.delete()
        await message.channel.send(f"{message.author.mention}, please use this command in <#768529385161752669>", delete_after = 30)
        await message.delete()

class DailyActivityRepository:

    __slots__ = ()

    @classmethod
    def increment_message(cls, user_id: int, guild_id: int):
        (DailyActivity
            .insert(user_id = user_id, guild_id = guild_id, date = datetime.date.today(), message_count = 1)
            .on_conflict(update = {DailyActivity.message_count: DailyActivity.message_count + 1})
            .execute())

    @classmethod
    def get_message_count(cls, user_id: int, guild_id: int, before: datetime.datetime, after = datetime.datetime) -> int:
        activity = (DailyActivity
            .select(peewee.fn.SUM(DailyActivity.message_count).alias("total_message_count"))
            .where(DailyActivity.guild_id == guild_id)
            .where(DailyActivity.user_id == user_id)
            .where(DailyActivity.date <= before)
            .where(DailyActivity.date >= after)
            .first()
        )

        if activity is None or activity.total_message_count is None:
            return 0
        else:
            return activity.total_message_count

class DailyActivityHelper:
    __slots__ = ()

    active_role_id    = 761260319820873809
    talkative_role_id = 761358543998681150
    lurkers_role_id   = 730025383189151744

    @classmethod
    def get_weekly_message_count(cls, user_id: int, guild_id: int):
        before               = datetime.date.today()
        after                = datetime.date.today() - datetime.timedelta(days = before.isoweekday())
        return DailyActivityRepository.get_message_count(user_id, guild_id, before, after)

    @classmethod
    def role_should_have(cls, guild: discord.Guild, weekly_message_count: int) -> discord.Role:
        if guild.id != Mouse.guild_id:
            return None

        if weekly_message_count >= 100:
            return guild.get_role(cls.talkative_role_id)
        if weekly_message_count >= 20:
            return guild.get_role(cls.active_role_id)
        if weekly_message_count >= 0:
            return guild.get_role(cls.lurkers_role_id)

    @classmethod
    async def synchronise_roles(cls, member: discord.Member, role_to_assign: discord.Role):
        all_roles = (cls.active_role_id, cls.talkative_role_id, cls.lurkers_role_id)

        if role_to_assign is None:
            return

        if role_to_assign in member.roles:
            return

        roles_to_remove = []
        for member_role in member.roles:
            if member_role.id != role_to_assign.id and member_role.id in all_roles:
                roles_to_remove.append(member_role)

        if len(roles_to_remove) > 0:
            await member.remove_roles(*roles_to_remove)

        await member.add_roles(role_to_assign)
