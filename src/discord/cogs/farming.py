import random
import asyncio

import requests
import discord
from discord.ext import commands

import src.config as config
from src.discord.cogs.core import BaseCog

class FarmingCog(BaseCog, name = "Farming"):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(name = "farm")
    async def farm(self, ctx):
        pass

def setup(bot):
    bot.add_cog(FarmingCog(bot))