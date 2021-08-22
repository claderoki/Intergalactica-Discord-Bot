import asyncio
import datetime

import discord
from discord.ext import commands
import requests

from src.models import Word, Human
import src.config as config
import src.games.blackjack as blackjack
import src.games.slotmachine as slotmachine
import src.games.tictactoe as tictactoe
import src.games.hangman as hangman
from src.games.game.base import AiIdentity, DiscordIdentity
from src.discord.cogs.core import BaseCog
from src.utils.general import html_to_discord

class Games(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

    async def get_members(self, ctx, timeout = 15, gold_needed = 0, min_members = None, max_members = None):
        if isinstance(ctx.channel, discord.DMChannel):
            return [ctx.author]

        creator = ctx.author
        members = [creator]
        emojis = {"join": "✅", "start": "💪"}

        embed = discord.Embed(color = ctx.guild_color)
        lines = []
        lines.append(f"{emojis['join']}: join the game")
        lines.append(f"{emojis['start']}: start the game (creator only)")
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
                    human = self.bot.get_human(user = user)
                    if human.gold < gold_needed:
                        asyncio.gather(message.channel.send(f"{user.mention}, you do not have enough gold to join this game. Gold needed: {gold_needed}"))
                        return False
                members.append(user)
                embed = message.embeds[0]
                embed.description += f"\n{user.mention}"
                asyncio.gather(message.edit(embed = embed))
                if max_members is not None and len(members) >= max_members:
                    return True

            return False

        try:
            await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            asyncio.gather(message.clear_reactions(), return_exceptions = False)
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
        ctx.raise_if_not_enough_gold(cost)
        players = []

        task = asyncio.create_task(get_word_details())
        members = await self.get_members(ctx, timeout = timeout, gold_needed = cost)
        for member in members:
            players.append(hangman.game.Player(DiscordIdentity(member), cost))

        while not task.done():
            await asyncio.sleep(1)

        result = task.result()

        game = hangman.game.Game(players, result["word"], hangman.ui.DiscordUI(ctx))
        game.word_definition = result["definition"]
        await game.start()

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def tictactoe(self, ctx, timeout : int = 30):
        players = []

        members = await self.get_members(ctx, timeout = timeout, max_members = 1)
        i = 1
        for member in members:
            players.append(tictactoe.game.Player(DiscordIdentity(member), i))
            i += 1
        if len(members) == 1:
            players.append(tictactoe.game.AIPlayer(AiIdentity(f"AI #{i}"), i))

        game = tictactoe.game.Game(players, tictactoe.ui.DiscordUI(ctx))
        await game.start()

def setup(bot):
    bot.add_cog(Games(bot))

def get_random_word():
    max = 3
    for i in range(max):
        word = get_single_random_word()
        if "-" not in word or i == max-1:
            return word

def get_single_random_word():
    url = "https://api.wordnik.com/v4/words.json/randomWord"
    params = {
        "api_key": config.environ["wordnik_api_key"],
        "hasDictionaryDef": True,
        "minLength": 6,
        "minCorpusCount": 100,
        "minDictionaryCount": 5
    }
    request = requests.get(url, params = params)
    return request.json()["word"]

def get_word_definition(word):
    url = f"https://api.wordnik.com/v4/word.json/{word}/definitions"
    params = {
        "api_key": config.environ["wordnik_api_key"],
        "limit": 1,
        "includeRelated": False,
    }
    request = requests.get(url, params = params)
    try:
        return html_to_discord(request.json()[0]["text"])
    except:
        pass

async def get_word_details() -> dict:
    word = get_random_word()
    definition = get_word_definition(word)
    return {"word": word, "definition": definition}
