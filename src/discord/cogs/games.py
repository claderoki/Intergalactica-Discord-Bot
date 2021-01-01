import asyncio
import datetime

import discord
from discord.ext import commands

from src.models import Word
import src.config as config
import src.games.blackjack as blackjack
import src.games.slotmachine as slotmachine
import src.games.hangman as hangman
from src.games.game.base import DiscordIdentity

class Games(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def get_members(self, ctx, timeout = 15):
        members = [ctx.author]
        join_emoji = "✅"

        embed = discord.Embed(color = ctx.guild_color)
        embed.description = f"React with {join_emoji} to join\nCurrent players:\n{members[0].mention}"
        embed.set_footer(text = "Game will start at")
        embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds = timeout)
        message = await ctx.send(embed = embed)
        asyncio.gather(message.add_reaction(join_emoji))

        def check(reaction, user):
            if str(reaction.emoji) == join_emoji and not user.bot:
                if user.id not in [x.id for x in members]:
                    members.append(user)
                    embed = message.embeds[0]
                    embed.description += f"\n{user.mention}"
                    asyncio.gather(message.edit(embed = embed))
            return False

        try:
            await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
        except asyncio.TimeoutError:
            return members

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
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def hangman(self, ctx, timeout : int = 30):
        players = []

        members = await self.get_members(ctx, timeout = timeout)
        for member in members:
            players.append(hangman.game.Player(DiscordIdentity(member), 5))

        game = hangman.game.Game(players, Word.get_random().value, hangman.ui.DiscordUI(ctx))
        await game.start()

def setup(bot):
    bot.add_cog(Games(bot))