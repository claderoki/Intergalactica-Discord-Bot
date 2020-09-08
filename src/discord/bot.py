import pathlib
import json
import asyncio
import random

import emoji
import discord

import src.config as config
from src.models import Translation
from src.wrappers.openweathermap import OpenWeatherMapApi

from discord.ext import commands

class Locus(commands.Bot):
    sendables = \
    (
        commands.errors.BotMissingPermissions,
        commands.errors.MissingRequiredArgument
    )

    ignorables = \
    (
        commands.errors.CommandNotFound
    )

    def __init__(self, prefix = "/"):
        if config.mode != config.Mode.production:
            prefix = "."

        super().__init__(command_prefix = prefix)

        # pathlib.Path(config.data_folder).mkdir(parents=True, exist_ok=True)

        self.load_translations()

        self.load_all_cogs()

        self.owm_api = OpenWeatherMapApi(config.owm_key)

        self.before_invoke(self.before_any_command)



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

        # for unicode_name in ("up_arrow", "down_arrow"):
        #     reaction = emoji.emojize(f":{unicode_name}:")
        #     await message.add_reaction(reaction)


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
