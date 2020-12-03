import asyncio
import datetime

import discord
from discord.ext import commands

import src.config as config
from src.discord.helpers.converters import CountryConverter
import src.discord.helpers.pretty as pretty

from src.models import Human, database
from src.discord.errors.base import SendableException

class CovidCog(discord.ext.commands.Cog, name = "Covid"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    def get_base_embed(self, guild) -> discord.Embed:
        embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        return embed

    @commands.command()
    async def covid(self, ctx, country : CountryConverter = None):
        human, _ = Human.get_or_create(user_id = ctx.author.id)
        country = country or human.country
        if country is None:
            raise SendableException(ctx.translate("no_country_selected"))

        status = country.covid_status

        table = pretty.Table()
        table.add_row(pretty.Row(("😷 Cases", status["active"])))
        table.add_row(pretty.Row(("💀 Deaths", status["deaths"])))
        table.add_row(pretty.Row(("💉 Recovered", status["recovered"])))

        embed = self.get_base_embed(ctx.guild)
        embed.description = table.generate()

        # embed.set_footer(text = "Last update")
        # embed.timestamp = datetime.datetime.utcfromtimestamp(status["last_update"])
        asyncio.gather(ctx.send(embed = embed))



def setup(bot):
    bot.add_cog(CovidCog(bot))