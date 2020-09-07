import discord
from discord.ext import commands

import src.config as config
# from src.discord.helpers.waiters import ReactionWaiter

class Games(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def get_players(self, timeout=15.0):
        players = []


    @commands.command()
    async def blackjack(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Games(bot))