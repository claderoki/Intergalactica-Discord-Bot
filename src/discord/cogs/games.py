import asyncio
import datetime

import discord
from discord.ext import commands

from src.models import Word, Human
import src.config as config
import src.games.blackjack as blackjack
import src.games.slotmachine as slotmachine
import src.games.hangman as hangman
from src.games.game.base import DiscordIdentity

class Games(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def get_members(self, ctx, timeout = 15, gold_needed = 0):
        creator = ctx.author
        members = [creator]
        emojis = {"join": "✅", "start": "💪"}

        embed = discord.Embed(color = ctx.guild_color)
        lines = []
        lines.append(f"{emojis['join']}: join the game")
        lines.append(f"{emojis['start']}: start the game (creater only)")
        lines.append(f"Current players:\n{members[0].mention} (creator)")

        embed.description = "\n".join(lines)
        embed.set_footer(text = "Game will start at")
        embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds = timeout)
        message = await ctx.send(embed = embed)
        add = lambda x : message.add_reaction(x)
        asyncio.gather(*[add(x) for x in emojis.values()])

        def check(reaction, user):
            if user.bot:
                return

            emoji = str(reaction.emoji)

            if emoji == emojis["start"] and user.id == creator.id:
                return True

            elif emoji == emojis["join"] and user.id not in [x.id for x in members]:
                if gold_needed is not None and gold_needed > 0:
                    human, _ = Human.get_or_create(user_id = user.id)
                    if human.gold < gold_needed:
                        asyncio.gather(message.channel.send(f"{user.mention}, you do not have enough gold to join this game. Gold needed: {gold_needed}"))
                        return False
                members.append(user)
                embed = message.embeds[0]
                embed.description += f"\n{user.mention}"
                asyncio.gather(message.edit(embed = embed))
            return False

        try:
            await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            asyncio.gather(message.clear_reactions())
            return members

    @commands.command()
    async def blackjack(self, ctx):
        cost = 5
        ctx.raise_if_not_enough_gold(cost)
        player = blackjack.game.Player(5, ctx.author)
        game = blackjack.game.Game(player, blackjack.ui.DiscordUI(ctx))
        await game.start()

    @commands.max_concurrency(1, per = commands.BucketType.user)
    @commands.command(aliases = ["slots"])
    async def slotmachine(self, ctx):
        ctx.raise_if_not_enough_gold(3)
        game = slotmachine.game.Game(slotmachine.ui.DiscordUI(ctx))
        await game.start()

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def hangman(self, ctx, timeout : int = 30):
        cost = 5
        ctx.raise_if_not_enough_gold(5)
        players = []

        members = await self.get_members(ctx, timeout = timeout, gold_needed = cost)
        for member in members:
            players.append(hangman.game.Player(DiscordIdentity(member), cost))

        game = hangman.game.Game(players, Word.get_random().value, hangman.ui.DiscordUI(ctx))
        await game.start()

def setup(bot):
    bot.add_cog(Games(bot))