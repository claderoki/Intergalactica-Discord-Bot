import pathlib
import json
import asyncio
import random
import os
from enum import Enum

import emoji
import discord
from discord.ext import commands

import src.config as config
from src.wrappers.openweathermap import OpenWeatherMapApi

class Locus(commands.Bot):

    class Mode(Enum):
        production = 1
        development = 2

    sendables = \
    (
        commands.errors.BotMissingPermissions,
        commands.errors.MissingRequiredArgument
    )

    ignorables = \
    (
        commands.errors.CommandNotFound
    )

    def __init__(self, mode, prefix = "/", ):
        self.mode = mode
        self.production = mode == self.Mode.production

        if not self.production:
            prefix = "."

        self.setup_environmental_variables()

        super().__init__(command_prefix = prefix)

        self.owm_api = OpenWeatherMapApi(os.environ["owm_key"])

        self.load_translations()
        self.load_all_cogs()

        self.before_invoke(self.before_any_command)

    def print_info(self):
        print("--------------------")
        print(f"Mode={self.mode.name}")
        print(f"Path={config.path}")
        print(f"Prefix={self.command_prefix}")
        print("--------------------")


    def setup_environmental_variables(self):
        if not self.production:
            try:
                with open(config.path + "/env") as f:
                    for line in f.read().splitlines():
                        key, value = line.split("=")
                        os.environ[key] = value
            except FileNotFoundError:
                with open(config.path + "/env", "w") as f:
                    lines = []
                    for var in ("mysql_user", "mysql_password", "mysql_port", "mysql_host", "discord_token", "owm_key"):
                        lines.append(f"{var}=")
                    f.write("\n".join(lines))
                raise Exception("Please fill in the 'env' file.")
    

    def load_cog(self, name):
        self.load_extension("src.discord.cogs." + name)

    def load_all_cogs(self):
        cogs = ("profile", "conversions", "management", "poll")

        for cog in cogs:
            self.load_cog(cog)

    def load_translations(self):
        with open(config.path + "/data/translations.json") as f:
            self.translations = json.loads(f.read())


    def get_random_color(self, start_range=80, end_range=255):
        # from 80 to 255 because most people use the dark theme, and anything under 80 is too bright to be comfortably visible.
        if end_range > 255:
            end_range = 255

        if start_range < 0:
            start_range = 0

        r, g, b = [random.randint(start_range, end_range) for _ in range(3)]
        random_color = discord.Colour(0).from_rgb(r, g, b)
        return random_color


    async def vote_for(self, message):
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")

    async def before_any_command(self, ctx):

        ctx.translate = self.translate

        ar = lambda x: ctx.message.add_reaction(x)

        ctx.vote = lambda: self.vote_for(ctx.message)
        ctx.success = lambda: ctx.message.add_reaction("✅")
        ctx.error = lambda: ctx.message.add_reaction("❌")



    async def on_command_error(self, ctx, exception):

        if isinstance(exception, self.sendables):
            return await ctx.send(str(exception))

        if isinstance(exception, self.ignorables):
            return

        raise exception

    async def on_ready(self):
        self.print_info()
        print("Ready")


    # def translate(self, key, locale = "en_US"):
    #     try:
    #         translation = Translation.get(locale = locale, message_key = key)
    #         return translation.translation
    #     except Translation.DoesNotExist:
    #         return key

    def translate(self, key, locale = "en_US"):
        for translation in self.translations:
            if key == translation["message_key"]:
                return translation["translation"]

        return key



class Embed:
    @classmethod
    def warning(cls, message):
        return discord.Embed( description = message, color = discord.Color.red() )


    @classmethod
    def success(cls, message):
        return discord.Embed( description = message, color = discord.Color.green() )
