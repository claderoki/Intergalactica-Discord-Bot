import pathlib
import json
import asyncio
import random
import os
from enum import Enum
import io

import requests
import emoji
import discord
from discord.ext import commands

import src.config as config
from src.wrappers.openweathermap import OpenWeatherMapApi
from src.wrappers.color_thief import ColorThief
from src.models import Settings, Translation, database

class Locus(commands.Bot):
    _dominant_colors = {}

    sendables = \
    (
        commands.errors.BotMissingPermissions,
        commands.errors.MissingRequiredArgument,
        commands.errors.MissingPermissions,
        commands.errors.PrivateMessageOnly,
        commands.errors.NoPrivateMessage
    )

    ignorables = \
    (
        commands.errors.CommandNotFound
    )

    def __init__(self, mode, prefix = "/", ):
        self.mode = mode
        self.production = mode == config.Mode.production
        self.missing_translations = {}

        if not self.production:
            prefix = "."

        super().__init__(command_prefix = prefix)

        self.owm_api = OpenWeatherMapApi(os.environ["owm_key"])

        self.load_all_cogs()

        self.before_invoke(self.before_any_command)

    def print_info(self):
        print("--------------------")
        print(f"Mode={self.mode.name}")
        print(f"Path={config.path}")
        print(f"Prefix={self.command_prefix}")
        print("--------------------")

    def base_embed(self, **kwargs) -> discord.Embed:
        user = self.user
        embed = discord.Embed(color = self.get_dominant_color(None), **kwargs)
        return embed.set_author(name = user.name, icon_url = user.avatar_url)



    async def store_file(self, file, filename) -> str:
        """This function stores a file in the designated storage channel, it returns the url of the newly stored image."""

        storage_channel = (await self.application_info()).owner
        # storage_channel = self.get_channel(755895328745455746)

        if isinstance(file, io.BytesIO):
            f = file
        else:
            f = io.BytesIO(file)

        msg = await storage_channel.send(file=discord.File(fp=f, filename=filename))

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


    def get_dominant_color(self, guild):
        obj = guild if guild is not None else self.user

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
            if guild.id == 742146159711092757: #intergalactica
                return guild

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
            "inactive",
            "staff_communication",
        ]

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

    async def vote_for(self, message):
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")

    async def before_any_command(self, ctx):

        ctx.translate = self.translate

        ar = lambda x: ctx.message.add_reaction(x)

        ctx.vote = lambda: self.vote_for(ctx.message)
        ctx.success = lambda: ctx.message.add_reaction("✅")
        ctx.error = lambda: ctx.message.add_reaction("❌")

        ctx.guild_color = self.get_dominant_color(ctx.guild)


    async def on_command_error(self, ctx, exception):

        if isinstance(exception, self.sendables):
            return await ctx.send(str(exception))

        if isinstance(exception, self.ignorables):
            return

        if isinstance(exception, commands.errors.CommandInvokeError):
            if isinstance(exception.original, Settings.DoesNotExist):
                with database:
                    Settings.get_or_create(guild_id = ctx.guild.id)
                await ctx.reinvoke(restart = True)
                return

        raise exception

    async def on_ready(self):
        self.print_info()
        print("Ready")


    def translate(self, key, locale = "en_US"):
        if locale not in self.missing_translations:
            self.missing_translations[locale] = set()
        
        missing_translations = self.missing_translations[locale]

        with database:
            try:
                translation = Translation.get(locale = locale, message_key = key)
                if key in missing_translations:
                    missing_translations.remove(key)
                return translation.value
            except Translation.DoesNotExist:
                missing_translations.add(key)
                return key

class Embed:
    @classmethod
    def warning(cls, message):
        return discord.Embed( description = message, color = discord.Color.red() )


    @classmethod
    def success(cls, message):
        return discord.Embed( description = message, color = discord.Color.green() )
