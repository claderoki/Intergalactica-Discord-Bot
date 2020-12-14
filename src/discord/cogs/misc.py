import random
import asyncio

import requests
import discord
from discord.ext import commands

import src.config as config

class MiscCog(commands.Cog, name = "Misc"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.command()
    async def urban(self, ctx, *, query):
        url = f"https://api.urbandictionary.com/v0/define?term={query}"
        request = requests.get(url)
        # print(request.json())
        json = request.json()

        embed = discord.Embed(color = ctx.guild_color)
        for definition in json["list"]:
            embed.title = definition["word"]
            embed.description = definition["definition"]
            embed.description += f"\n\n{definition['example']}"

            asyncio.gather(ctx.send(embed = embed))
            break


def setup(bot):
    bot.add_cog(MiscCog(bot))