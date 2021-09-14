import datetime
import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
from src.discord.cogs.core import BaseCog
# from src.wrappers.hue_bridge import GetLightsCall, HueBridgeCall, HueBridgeCache, AuthenticateCall, Light

class Personal(BaseCog):
    pass

def setup(bot):
    bot.add_cog(Personal(bot))
