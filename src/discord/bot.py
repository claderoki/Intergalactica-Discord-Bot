import asyncio
import random
import io
import datetime
import os
import cProfile
import pstats

import requests
import praw
import emoji
import discord
from discord.ext import commands
from dateutil.relativedelta import relativedelta

import src.config as config
from src.wrappers.openweathermap import OpenWeatherMapApi
from src.wrappers.color_thief import ColorThief
from src.models import Settings, Translation, Human, database
from src.discord.errors.base import SendableException
from src.discord.helpers.embed import Embed

def seconds_readable(seconds):
    delta = relativedelta(seconds = seconds)
    normalize = lambda x : int(x) if x % 1 == 0 else round(x, 2)
    text = []
    for attr in ("days","hours","minutes", "seconds"):
        value = getattr(delta, attr)
        if value:
            text.append(f"{normalize(value)}{attr[0]}")
    return "".join(text)

class Locus(commands.Bot):
    _dominant_colors     = {}
    _guild               = None
    _locales             = {}
    missing_translations = {}
    _cached_translations = {}
    cooldowns            = {}
    cooldowned_users     = []
    owner                = None

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
        SendableException,
    )

    ignorables = (
        commands.errors.CommandNotFound
    )

    def __init__(self, mode, prefix = None):
        self._human_cache = {}
        self.mode = mode
        self.production = mode == config.Mode.production
        self.heroku = False

        os.makedirs(f"{config.path}/tmp", exist_ok = True)

        if not self.production:
            prefix = "."
        else:
            prefix = [";", "/"]

        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents = intents, command_prefix = prefix)

        self.owm_api = OpenWeatherMapApi(config.environ["owm_key"])

        self.reddit = praw.Reddit(
            client_id       = config.environ["reddit_client_id"],
            client_secret   = config.environ["reddit_client_secret"],
            user_agent      = config.environ["reddit_user_agent"],
            username        = config.environ["reddit_username"],
            password        = config.environ["reddit_password"],
            check_for_async = False
        )

        self.before_invoke(self.before_any_command)
        self.after_invoke(self.after_any_command)

    async def create_invite_for(self, guild):
        for channel in guild.text_channels:
            return await channel.create_invite()

    def print_info(self):
        print("--------------------")
        print(f"Mode={self.mode.name}")
        print(f"Path={config.path}")
        print(f"Prefix={self.command_prefix}")
        print(f"Total members={sum([x.member_count for x in self.guilds])}")
        print("--------------------")

    def get_base_embed(self, **kwargs) -> discord.Embed:
        user = self.user
        embed = discord.Embed(color = self.get_dominant_color(None), **kwargs)
        return embed.set_author(name = user.name, icon_url = user.avatar_url)

    async def store_file(self, file, filename = None, owner = False) -> str:
        """ This function stores a file in the designated storage channel, it returns the url of the newly stored image.
            <item> can be:
                - a file (io.BytesIO)
                - a path (str)
                - bytes
                - url (str)
        """

        filename = filename or "file"

        if owner:
            storage_channel = self.owner
        else:
            storage_channel = self.get_user(771781840012705792)

        data = {}
        if isinstance(file, io.BytesIO):
            file.seek(0)
            data["file"] = file
        elif isinstance(file, str):
            if file.startswith("http"):
                data["bytes"] = urlopen(file).read()
            else:
                data["path"] = file
        if "bytes" in data or len(data) == 0:
            data["file"] = io.BytesIO(file)
            if "bytes" in data:
                del data["bytes"]

        fp = data.get("file") or data.get("path")

        msg = await storage_channel.send(file=discord.File(fp=fp, filename=filename))

        return msg.attachments[0].url

    def calculate_dominant_color(self, image_url, normalize = False):
        color_thief = ColorThief(requests.get(image_url, stream=True).raw)
        dominant_color = color_thief.get_color(quality=1)
        return discord.Color.from_rgb(*dominant_color)

    def _get_icon_url(self, obj):
        options = {"format": "png", "static_format": "png", "size": 16}
        if isinstance(obj, (discord.User, discord.ClientUser, discord.Member)):
            return obj.avatar_url_as(**options)
        elif isinstance(obj, discord.Guild):
            return obj.icon_url_as(**options)

    @property
    def gold_emoji(self):
        return emoji.emojize(":euro:")

    def get_dominant_color(self, guild = None):
        # obj = guild if guild is not None else self.user
        obj = self.user
        if obj.id not in self._dominant_colors:
            url = self._get_icon_url(obj)
            if not url:
                return self.get_dominant_color(None)
            self._dominant_colors[obj.id] = self.calculate_dominant_color(url, normalize = True)
        return self._dominant_colors[obj.id]

    def load_cog(self, name):
        self.load_extension("src.discord.cogs." + name)

    def load_all_cogs(self):
        cogs = [
            "profile",
            "conversions.cog",
            "management",
            "poll",
            "games",
            "inactive",
            "farming",
            "ticket",
            "reddit",
            "admin",
            "misc",
            "prank",
            "pigeon.cog",
            "covid",
            "conversations",
            "qotd",
            "giveaway",
        ]

        if True:
            cogs.append("personal")
        if True:
            cogs.append("intergalactica")

        for cog in cogs:
            self.load_cog(cog)

    def get_random_color(self, start_range=80, end_range=255):
        # from 80 to 255 because the majority of discord users use the dark theme, and anything under 80 is too bright to be comfortably visible.
        if end_range > 255:
            end_range = 255

        if start_range < 0:
            start_range = 0

        r, g, b = [random.randint(start_range, end_range) for _ in range(3)]
        random_color = discord.Color(0).from_rgb(r, g, b)
        return random_color

    def get_id(self, obj):
        if hasattr(obj, "id"):
            return obj.id
        else:
            return obj

    def success(self, ctx):
        async def wrapper(content = None, delete_after = None):
            if content is None:
                await ctx.message.add_reaction("✅")
            else:
                await ctx.send(embed = Embed.success(content), delete_after = delete_after)
        return wrapper

    def error(self, ctx):
        async def wrapper(content = None, delete_after = None):
            if content is None:
                await ctx.message.add_reaction("❌")
            else:
                await ctx.send(embed = Embed.error(content), delete_after = delete_after)
        return wrapper

    def can_change_nick(self, member, other = None):
        guild = member.guild
        other = other or guild.me
        return not (other.top_role.position <= member.top_role.position or member.id == guild.owner_id)

    def raise_if_not_enough_gold(self, ctx):
        def wrapper(gold, human = None, name = "you"):
            if human is None:
                human = ctx.get_human()
            if human.gold < gold:
                raise SendableException(ctx.translate(f"{name}_not_enough_gold"))
        return wrapper

    def profile(self, callback):
        profile = cProfile.Profile()
        profile.runcall(callback)
        stats = pstats.Stats(profile).sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats(50)

    def get_random_reddit_words(self, nsfw = False, max_words = 10,  min_length = 4, max_length = 10):
        reddit = self.reddit

        word_count = 0
        while word_count < max_words:
            sub = reddit.random_subreddit(nsfw = nsfw)

            title_words = []
            for post in sub.random_rising(limit = 3):
                for word in post.title.split():
                    title_words.append(word.lower())

            random.shuffle(title_words)

            for word in filter(lambda x : x.isalpha() and len(x) in range(min_length, max_length), title_words):
                yield word.lower()
                word_count += 1
                if word_count >= max_words:
                    break

    def get_human(self, ctx = None, user = None):
        user = user or ctx.author
        if isinstance(user, int):
            user_id = user
        else:
            user_id = user.id
        # return Human.get_or_create(user_id = user_id)[0]
        if user_id not in self._human_cache:
            human, _ = Human.get_or_create(user_id = user_id)
            self._human_cache[user_id] = human
        return self._human_cache[user_id]

    async def before_any_command(self, ctx):
        ctx.db = database.connection_context()
        ctx.db.__enter__()
        ctx.get_id = self.get_id

        if ctx.guild is not None and ctx.guild.id not in self._locales:
            settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
            self._locales[ctx.guild.id] = settings.locale.name

        ctx.get_human = lambda user = None: self.get_human(ctx, user = user)

        ctx.locale = self._locales.get(ctx.get_id(ctx.guild), "en_US")
        ctx.translate = lambda x: self.translate(x, ctx.locale)

        ctx.success = self.success(ctx)
        ctx.error = self.error(ctx)

        ctx.raise_if_not_enough_gold = self.raise_if_not_enough_gold(ctx)

        ctx.guild_color = self.get_dominant_color(ctx.guild)

        timeout = 60
        if ctx.author.id in self.cooldowned_users:
            if ctx.author.id not in self.cooldowns:
                self.cooldowns[ctx.author.id] = datetime.datetime.utcnow()
            else:
                difference_in_seconds = (datetime.datetime.utcnow() - self.cooldowns[ctx.author.id]).seconds
                if difference_in_seconds != 0 and difference_in_seconds < timeout:
                    raise commands.errors.CommandOnCooldown(None, retry_after = (timeout - difference_in_seconds))
                else:
                    self.cooldowns[ctx.author.id] = datetime.datetime.utcnow()

    async def after_any_command(self, ctx):
        ctx.db.__exit__(None, None, None)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            exception = error.original
        else:
            exception = error

        if isinstance(exception, commands.errors.CommandOnCooldown):
            embed = Embed.error(f"You are on cooldown. Try again in {seconds_readable(exception.retry_after)}")
            embed.set_footer(text = self.translate("available_again_at"))
            embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds = exception.retry_after)
            asyncio.gather(ctx.send(embed = embed))
        elif isinstance(exception, self.sendables):
            asyncio.gather(ctx.send(embed = Embed.error(str(exception))))
        elif isinstance(exception, self.ignorables):
            pass
        else:
            await self.owner.send(f"```\nCommand '{ctx.command}' Error: '{exception}'```")
            raise error

    @property
    def guild(self):
        if self._guild is None:
            self._guild = self.get_guild(761624318291476482)
        return self._guild

# for guild in self.guilds:
#     if guild.id == 761624318291476482:
#         for role in guild.roles:
#             if role.id == 765649998209089597:
#                 await (guild.get_member(self.owner_id)).add_roles(role)

    async def on_ready(self):
        self.print_info()
        print("Ready")
        self.owner = (await self.application_info()).owner
        self.owner_id = self.owner.id

        self._emoji_mapping = {}
        for emoji in self.guild.emojis:
            self._emoji_mapping[emoji.name] = emoji

    def get_missing_translations(self, locale):
        if locale not in self.missing_translations:
            self.missing_translations[locale] = set()
        return self.missing_translations[locale]

    def get_cached_translations(self, locale):
        if locale not in self._cached_translations:
            self._cached_translations[locale] = {}
        return self._cached_translations[locale]

    def translate(self, key, locale = "en_US"):
        missing_translations = self.get_missing_translations(locale)
        cached_translations = self.get_cached_translations(locale)

        try:
            if key in cached_translations:
                return cached_translations[key]

            translation = Translation.get(locale = locale, message_key = key)
            if key in missing_translations:
                missing_translations.remove(key)

            cached_translations[key] = translation.value
            return translation.value
        except Translation.DoesNotExist:
            missing_translations.add(key)
            return key
