import asyncio

import discord
import requests
from discord.ext import commands

from src.discord.cogs.core import BaseCog


class MiscCog(BaseCog, name="Misc"):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    @commands.is_nsfw()
    async def urban(self, ctx, *, query):
        url = f"https://api.urbandictionary.com/v0/define?term={query}"
        request = requests.get(url)
        json = request.json()

        embed = discord.Embed(color=ctx.guild_color)
        for definition in json["list"]:
            embed.title = definition["word"]
            embed.description = definition["definition"]
            embed.description += f"\n\n{definition['example']}"

            asyncio.gather(ctx.send(embed=embed))
            break

    @commands.command()
    async def fact(self, ctx):
        url = "https://uselessfacts.jsph.pl/random.json?language=en"
        request = requests.get(url)
        json = request.json()
        embed = discord.Embed(color=ctx.guild_color)
        embed.description = json["text"].replace('`','\'')
        embed.title = "Useless fact"
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx):
        """Gives an invite link so you can add the bot"""
        await ctx.send(f"https://discord.com/api/oauth2/authorize?client_id={ctx.bot.user.id}&scope=applications.commands+bot&permissions=0")


async def setup(bot):
    await bot.add_cog(MiscCog(bot))
