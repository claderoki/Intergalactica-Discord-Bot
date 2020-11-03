import discord
from discord.ext import commands

import src.config as config
import src.games.blackjack as blackjack
import src.games.slotmachine as slotmachine
import src.games.hangman as hangman
from src.games.game.base import DiscordIdentity

class Games(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def get_players(self, timeout=15.0):
        players = []

    @commands.command()
    async def blackjack(self, ctx):
        player = blackjack.game.Player(5, ctx.author)
        game = blackjack.game.Game(player, blackjack.ui.DiscordUI(ctx))
        await game.start()

    @commands.command(aliases = ["slots"])
    async def slotmachine(self, ctx):
        game = slotmachine.game.Game(slotmachine.ui.DiscordUI(ctx))
        await game.start()

    @commands.command()
    async def hangman(self, ctx):
        players = []

        players.append(hangman.game.Player(DiscordIdentity(ctx.author), 5))
        game = hangman.game.Game(players, "appelsap", hangman.ui.DiscordUI(ctx))
        await game.start()


def setup(bot):
    bot.add_cog(Games(bot))