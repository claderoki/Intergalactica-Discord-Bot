import asyncio

import discord
from discord.ext import commands

import src.disc.helpers.pretty as pretty
from src.disc.cogs.core import BaseCog
from src.disc.errors.base import SendableException
from src.disc.helpers import ColorHelper
from src.disc.helpers.converters import CountryConverter


class CovidCog(BaseCog, name="Covid"):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    def get_base_embed(self, guild) -> discord.Embed:
        embed = discord.Embed(color=ColorHelper.get_dominant_color())
        return embed

    @commands.command()
    async def covid(self, ctx, country: CountryConverter = None):
        human = ctx.get_human()
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
        asyncio.gather(ctx.send(embed=embed))


async def setup(bot):
    await bot.add_cog(CovidCog(bot))
