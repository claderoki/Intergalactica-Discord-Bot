import pathlib
import json
import asyncio
import random
import os
from enum import Enum
import io
import datetime

import requests
import praw
import emoji
import discord
from discord.ext import commands
from dateutil.relativedelta import relativedelta

import src.config as config
from src.wrappers.openweathermap import OpenWeatherMapApi
from src.wrappers.color_thief import ColorThief
from src.models import Settings, Translation, NamedChannel, database
from src.discord.errors.base import SendableException
from src.discord.helpers.embed import Embed

def seconds_readable(seconds):
    fmt = "{delta.days} days {delta.hours} hours {delta.minutes} minutes {delta.seconds} seconds"
    delta = relativedelta(seconds = seconds)
    normalize = lambda x : int(x) if x % 1 == 0 else round(x, 2)
    text = []
    for attr in ('days','hours','minutes'):
        value = getattr(delta, attr)
        if value:
            text.append(f"{normalize(value)}{attr[0]}")
    return "".join(text)

class Locus(commands.Bot):
    _dominant_colors = {}
    _guild = None
    _locales = {}
    missing_translations = {}
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
        SendableException,
    )

    ignorables = (
        commands.errors.CommandNotFound
    )

    def __init__(self, mode, prefix = "/"):
        self.mode = mode
        self.production = mode == config.Mode.production
        self.heroku = False

        if not self.production:
            prefix = "."

        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents = intents, command_prefix = prefix)

        self.owm_api = OpenWeatherMapApi(os.environ["owm_key"])

        self.reddit = praw.Reddit(
            client_id=os.environ["reddit_client_id"],
            client_secret=os.environ["reddit_client_secret"],
            user_agent=os.environ["reddit_user_agent"]
        )

        self.before_invoke(self.before_any_command)
        self.after_invoke(self.after_any_command)

    def print_info(self):
        print("--------------------")
        print(f"Mode={self.mode.name}")
        print(f"Path={config.path}")
        print(f"Prefix={self.command_prefix}")
        print("--------------------")

    def render_template(self, name, **data):
        from weasyprint import HTML, CSS
        import jinja2

        path = f"{config.path}/src/templates/{name}"
        with open(f"{path}/{name}.html") as f:
            template = jinja2.Template(f.read())

        html = template.render(**data)

        with open(f"{path}/{name}.css") as f:
            _bytes = HTML(string = html, base_url = path).write_png(None,  stylesheets  = [CSS(string = f.read())] )
        return discord.File(fp = io.BytesIO(_bytes), filename = f"{name}.png")

    def get_base_embed(self, **kwargs) -> discord.Embed:
        user = self.user
        embed = discord.Embed(color = self.get_dominant_color(None), **kwargs)
        return embed.set_author(name = user.name, icon_url = user.avatar_url)

    async def store_file(self, file, filename = None) -> str:
        """ This function stores a file in the designated storage channel, it returns the url of the newly stored image.
            <item> can be:
                - a file (io.BytesIO)
                - a path (str)
                - bytes
                - url (str)
        """

        filename = filename or "file"

        storage_channel = (await self.application_info()).owner

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
        if isinstance(obj, (discord.User, discord.ClientUser)):
            return obj.avatar_url_as(**options)
        elif isinstance(obj, discord.Guild):
            return obj.icon_url_as(**options)

    @property
    def gold_emoji(self):
        return emoji.emojize(":euro:")

    def get_dominant_color(self, guild):
        # obj = guild if guild is not None else self.user
        obj = self.user
        if obj.id not in self._dominant_colors:
            url = self._get_icon_url(obj)
            if not url:
                return self.get_dominant_color(None)
            self._dominant_colors[obj.id] = self.calculate_dominant_color(url, normalize = True)
        return self._dominant_colors[obj.id]

    def mutual_guilds_with(self, user):
        return (x for x in self.guilds if x.get_member(user.id) is not None)

    async def guild_choice_for(self, user):
        guilds = list(self.mutual_guilds_with(user))

        if len(guilds) == 1:
            return guilds[0]

        for guild in guilds:
            #TODO: remove hard coding
            if guild.id == 742146159711092757: #intergalactica
                return guild
        #TODO: translate
        lines = ["Select the server."]

        i = 1
        for guild in guilds:
            lines.append(f"{guild.name}")
            i += 1

    def load_cog(self, name):
        self.load_extension("src.discord.cogs." + name)

    def load_all_cogs(self):
        cogs = [
            "profile",
            "conversions",
            "management",
            "poll",
            "games",
            "inactive",
            "ticket",
            "reddit",
            "admin",
            "prank",
            "pigeon",
        ]

        if False:
            cogs.append("personal")
        if True:
            cogs.append("intergalactica")

        for cog in cogs:
            self.load_cog(cog)

    def get_random_color(self, start_range=80, end_range=255):
        # from 80 to 255 because most people use the dark theme, and anything under 80 is too bright to be comfortably visible.
        if end_range > 255:
            end_range = 255

        if start_range < 0:
            start_range = 0

        r, g, b = [random.randint(start_range, end_range) for _ in range(3)]
        random_color = discord.Colour(0).from_rgb(r, g, b)
        return random_color

    def text_to_emojis(self, text):
        text = str(text)
        emojis = []

        for char in text:
            if char.isdigit():
                emoji_format = ":keycap_{char}:"
            elif char == "-":
                emoji_format = ":heavy_minus_sign:"
            elif char == ".":
                emoji_format = ":black_small_square:"
            else:
                emoji_format = ":regional_indicator_symbol_letter_{char}:"

            emojis.append(emoji.emojize(emoji_format.format(char = char), use_aliases=True))

        return emojis

    def get_id(self, obj):
        if hasattr(obj, "id"):
            return obj.id
        else:
            return obj

    async def after_any_command(self, ctx):
        ctx.db.__exit__(None, None, None)

    async def before_any_command(self, ctx):
        ctx.db = database.connection_context()
        ctx.db.__enter__()
        ctx.get_id = self.get_id

        if ctx.guild is None:
            locale_name = "en_US"
        else:
            if ctx.guild.id not in self._locales:
                settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
                self._locales[ctx.guild.id] = settings.locale.name

        ctx.translate = lambda x: self.translate(x, self._locales.get(ctx.get_id(ctx.guild), "en_US"))

        ctx.success = lambda: ctx.message.add_reaction("✅")
        ctx.error = lambda: ctx.message.add_reaction("❌")

        ctx.guild_color = self.get_dominant_color(ctx.guild)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            exception = error.original
        else:
            exception = error

        if isinstance(exception, commands.errors.CommandOnCooldown):
            embed = Embed.error(f"You are on cooldown. Try again in {seconds_readable(exception.retry_after)}")
            embed.set_footer(text = "Available again at")
            embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds = exception.retry_after)
            asyncio.gather(ctx.send(embed = embed))
        elif isinstance(exception, self.sendables):
            asyncio.gather(ctx.send(embed = Embed.error(str(exception))))
        elif isinstance(exception, self.ignorables):
            pass
        else:
            raise error

    @property
    def guild(self):
        if self._guild is None:
            self._guild = self.get_guild(761624318291476482)
        return self._guild

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

    def translate(self, key, locale = "en_US"):
        missing_translations = self.get_missing_translations(locale)
        try:
            translation = Translation.get(locale = locale, message_key = key)
            if key in missing_translations:
                missing_translations.remove(key)
            return translation.value
        except Translation.DoesNotExist:
            missing_translations.add(key)
            return key
