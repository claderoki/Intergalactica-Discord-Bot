import discord
from discord.ext import commands

import src.config as config
import src.games.blackjack as blackjack

class Games(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def get_players(self, timeout=15.0):
        players = []

    @commands.command()
    async def blackjack(self, ctx):
        
        players = []
        players.append(blackjack.game.Player(5, ctx.author))
        players.append(blackjack.game.Player(0))
        players.append(blackjack.game.Player(0))

        game = blackjack.game.Game(players, blackjack.ui.DiscordUI(ctx))
        await game.start()

def setup(bot):
    bot.add_cog(Games(bot))