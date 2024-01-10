import asyncio
import datetime
import os

import discord
import emoji
import praw
from dateutil.relativedelta import relativedelta
from discord.ext import commands

import src.config as config
from src.disc.errors.base import SendableException
from src.disc.helpers import ColorHelper
from src.disc.helpers.embed import Embed
from src.disc.helpers.general import Translator
from src.disc.helpers.waiters.base import Cancelled
from src.models import Human, database
from src.wrappers.openweathermap import OpenWeatherMapApi


def seconds_readable(seconds):
    delta = relativedelta(seconds=seconds)
    normalize = lambda x: int(x) if x % 1 == 0 else round(x, 2)
    text = []
    for attr in ("days", "hours", "minutes", "seconds"):
        value = getattr(delta, attr)
        if value:
            text.append(f"{normalize(value)}{attr[0]}")
    return "".join(text)


class Locus(commands.Bot):
    cooldowns = {}
    cooldowned_users = []
    owner = None

    sendables = (
        commands.errors.BotMissingPermissions,
        commands.errors.MissingRequiredArgument,
        commands.errors.MissingPermissions,
        commands.errors.PrivateMessageOnly,
        commands.errors.NoPrivateMessage,
        commands.errors.BadArgument,
        commands.errors.ConversionError,
        commands.errors.CommandOnCooldown,
        commands.errors.MemberNotFound,
        commands.errors.UserNotFound,
        commands.errors.ChannelNotFound,
        commands.errors.RoleNotFound,
        commands.errors.MaxConcurrencyReached,
        commands.errors.NotOwner,
        commands.errors.NSFWChannelRequired,
        commands.errors.CheckFailure,
        SendableException,
    )

    ignorables = (
        commands.errors.CommandNotFound,
        Cancelled,
    )

    def __init__(self, mode):
        self._human_cache = {}
        self.mode = mode
        self.production = mode == config.Mode.production
        self.heroku = False
        self.restarting = False

        os.makedirs(f"{config.path}/tmp", exist_ok=True)

        if not self.production:
            prefix = "."
        else:
            prefix = [";", "/"]

        intents = discord.Intents.all()
        super().__init__(intents=intents, command_prefix=prefix)

        self.owm_api = OpenWeatherMapApi(config.environ["owm_key"])

        self.reddit = praw.Reddit(
            client_id=config.environ["reddit_client_id"],
            client_secret=config.environ["reddit_client_secret"],
            user_agent=config.environ["reddit_user_agent"],
            username=config.environ["reddit_username"],
            password=config.environ["reddit_password"],
            check_for_async=False
        )

        self.before_invoke(self.before_any_command)
        self.after_invoke(self.after_any_command)

    def print_info(self):
        print("--------------------")
        print(f"Mode          = {self.mode.name}")
        print(f"Path          = {config.path}")
        print(f"Prefix        = {self.command_prefix}")
        print(f"Total members = {sum([x.member_count for x in self.guilds])}")
        print("--------------------")

    def get_base_embed(self, **kwargs) -> discord.Embed:
        user = self.user
        embed = discord.Embed(color=ColorHelper.get_dominant_color(), **kwargs)
        return embed.set_author(name=user.name, icon_url='https://images-ext-2.discordapp.net/external/V7zYwOVBg6jrf7W0p7zvPxBwtNSDhi0enFMPTwV4ZsQ/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/742365922244952095/710d9db4d90b2ad5be1b87a8510eb247.webp')

    def get_dominant_color(self, *args, **kwargs):
        return ColorHelper.get_dominant_color(*args, **kwargs)

    @property
    def gold_emoji(self):
        return emoji.emojize(":euro:")

    async def load_cog(self, name):
        await self.load_extension("src.disc.cogs." + name)

    async def load_all_cogs(self):
        cogs = [
            "profile",
            "conversions.cog",
            "management",
            "poll",
            "games",
            "inactive",
            "reddit",
            "reminders.cog",
            "admin",
            "misc",
            "prank",
            "milkyway.cog",
            "pigeon.cog",
            "gameroles.cog",
            "switch.cog",
            "custom.mouse.cog",
            "custom.hut.cog",
            "custom.c3po.cog",
            "custom.cam.cog",
            "custom.shared.cog",
            "birthdayreminders.cog",
            "inactivechannels.cog",
            "conversations",
            "welcoming.cog",
            "groups",
        ]

        if True:
            cogs.append("intergalactica")

        for cog in cogs:
            await self.load_cog(cog)

        await self.load_extension("src.disc.commands.pigeon.commands")

    @staticmethod
    def get_id(obj):
        if hasattr(obj, "id"):
            return obj.id
        else:
            return obj

    @staticmethod
    def success(ctx):
        async def wrapper(content=None, delete_after=None):
            if content is None:
                await ctx.message.add_reaction("✅")
            else:
                await ctx.send(embed=Embed.success(content), delete_after=delete_after)

        return wrapper

    @staticmethod
    def error(ctx):
        async def wrapper(content=None, delete_after=None):
            if content is None:
                await ctx.message.add_reaction("❌")
            else:
                await ctx.send(embed=Embed.error(content), delete_after=delete_after)

        return wrapper

    @staticmethod
    def can_change_nick(member, other=None):
        guild = member.guild
        other = other or guild.me
        return not (other.top_role.position <= member.top_role.position or member.id == guild.owner_id)

    @staticmethod
    def raise_if_not_enough_gold(ctx):
        def wrapper(gold, human=None, name="you"):
            if human is None:
                human = ctx.get_human()
            if human.gold < gold:
                raise SendableException(ctx.translate(f"{name}_not_enough_gold"))

        return wrapper

    def get_human(self, ctx=None, user=None):
        """Cached human, with updated gold."""
        user = user or ctx.author
        user_id = self.get_id(user)
        if user_id not in self._human_cache:
            human, _ = Human.get_or_create(user_id=user_id)
            self._human_cache[user_id] = human
        else:
            human = self._human_cache[user_id]
            # h = Human.select(Human.gold).where(Human.user_id == user_id).first()
            # human.gold = h.gold
            return human
        return self._human_cache[user_id]

    @staticmethod
    def translate(key, locale="en_US"):
        return Translator.translate(key, locale)

    async def before_any_command(self, ctx):
        ctx.db = database.connection_context()
        ctx.db.__enter__()

        ctx.translate = lambda x: Translator.translate(x, "en_US")

        ctx.get_id = self.get_id
        ctx.get_human = lambda user=None: self.get_human(ctx, user=user)

        ctx.success = self.success(ctx)
        ctx.error = self.error(ctx)

        ctx.raise_if_not_enough_gold = self.raise_if_not_enough_gold(ctx)

        ctx.guild_color = ColorHelper.get_dominant_color(ctx.guild)

        timeout = 60
        if ctx.author.id in self.cooldowned_users:
            if ctx.author.id not in self.cooldowns:
                self.cooldowns[ctx.author.id] = datetime.datetime.utcnow()
            else:
                difference_in_seconds = (datetime.datetime.utcnow() - self.cooldowns[ctx.author.id]).seconds
                if difference_in_seconds != 0 and difference_in_seconds < timeout:
                    raise commands.errors.CommandOnCooldown(None, retry_after=(timeout - difference_in_seconds))
                else:
                    self.cooldowns[ctx.author.id] = datetime.datetime.utcnow()

    async def after_any_command(self, ctx):
        ctx.db.__exit__(None, None, None)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            exception = error.original
        else:
            exception = error

        if isinstance(exception, commands.errors.MissingPermissions):
            await self.owner.send(f"```\nCommand '{ctx.command}' in '{ctx.author}' in {ctx.guild.id if ctx.guild else ''} Error: '{exception}'```")
        elif isinstance(exception, commands.errors.CommandOnCooldown):
            embed = Embed.error(f"You are on cooldown. Try again in {seconds_readable(exception.retry_after)}")
            embed.set_footer(text=self.translate("available_again_at"))
            embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=exception.retry_after)
            asyncio.gather(ctx.send(embed=embed))
        elif isinstance(exception, self.sendables):
            asyncio.gather(ctx.send(embed=Embed.error(str(exception))))
        elif not isinstance(exception, self.ignorables):
            await self.owner.send(f"```\nCommand '{ctx.command}' Error: '{exception}'```")
            raise error

    async def setup_hook(self):
        import src.disc.commands
        await self.load_all_cogs()
        self.tree.copy_global_to(guild=discord.Object(id=761624318291476482))
        await self.tree.sync(guild=discord.Object(id=761624318291476482))

    def log(self, message: str):
        if self.owner is not None:
            asyncio.gather(self.owner.send(message))
        else:
            print(f"Owner not initialized yet, logged: {message}")
