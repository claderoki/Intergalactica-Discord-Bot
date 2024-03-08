import asyncio
import math

import discord

from src.constants import GOLD_EMOJI
from .ui import UI


async def delete_message(message):
    try:
        await message.delete()
        return True
    except:
        return False


class DiscordUI(UI):
    def __init__(self, ctx):
        self.message = None
        self.mention_message = None
        self.ctx = ctx
        self.invalid_messages = 0
        self.timeout = 60

    def __check(self, word, letters_used, player):
        def __check2(message):
            dm = isinstance(message.channel, discord.DMChannel)

            if self.ctx.channel.id != message.channel.id:
                return False
            if player.identity.member.id != message.author.id:
                self.invalid_messages += 1
                return False
            if len(message.content) == 1 and " " not in message.content:
                letter = message.content.lower()
                if not dm:
                    asyncio.gather(delete_message(message))
                else:
                    self.invalid_messages += 1
                if letter not in letters_used:
                    return True
                else:
                    self.send_error(f"Letter '{letter}' has already been used")
            elif len(message.content) == len(word):
                if not dm:
                    asyncio.gather(delete_message(message))
                else:
                    self.invalid_messages += 1
                return True
            else:
                self.invalid_messages += 1
                return False

            return False

        return __check2

    def send_error(self, text, delete_after=10):
        asyncio.gather(self.ctx.error(text, delete_after=delete_after))

    async def get_guess(self, word, player, letters_used):
        try:
            guess = await self.ctx.bot.wait_for("message", check=self.__check(word, letters_used, player),
                                                timeout=self.timeout)
        except asyncio.TimeoutError:
            guess = None

        if self.mention_message is not None:
            asyncio.gather(delete_message(self.mention_message))

        return guess.content.lower() if guess is not None else None

    async def refresh_board(self, game, current_player=None):
        embed = discord.Embed(color=self.ctx.guild_color, title=" ".join(game.board))

        for player in game.players:
            if player.dead:
                continue

            length = len(str(player))

            embed.add_field(
                name=str(player),
                value=f">>> ```\n{self.game_states[player.incorrect_guesses]}```")

        guess_info = []
        guess_info.append("letters used: " + ", ".join([f"**{x}**" for x in sorted(game.letters_used)]))

        if len(game.words_used) > 0:
            guess_info.append("words tried: " + ", ".join(game.words_used))

        content = None
        if current_player is not None:
            content = current_player.identity.member.mention

        embed.add_field(name="\uFEFF", value="\n".join(guess_info), inline=False)
        if self.message is None or self.invalid_messages > 3:
            if self.message is not None:
                asyncio.gather(delete_message(self.message))
            self.message = await self.ctx.send(content=content, embed=embed)
            self.invalid_messages = 0
        else:
            asyncio.gather(self.message.edit(content=content, embed=embed))

        if current_player is not None and len(game.players) > 1:
            self.mention_message = await self.ctx.send(
                f"{current_player.identity.member.mention}, your turn! {self.timeout}s...", delete_after=self.timeout)

    async def stop(self, reason, game):
        embed = discord.Embed(title=f"Game has ended: {reason.value}", color=self.ctx.guild_color)
        lines = []

        bet_pool = sum([x.bet for x in game.players])
        bet_pool *= 1.25
        bet_pool += (15 * len(game.players))
        bet_pool = int(bet_pool)

        total_letters = len(game.word)
        players = sorted(game.players, key=lambda p: p.correct_guesses - (100 if p.dead else 0), reverse=True)
        i = 0
        for player in players:
            name = player.identity.member.mention
            if player.dead:
                player.identity.remove_points(player.bet)
                lines.append(f"{name}\nLost {GOLD_EMOJI} **{player.bet}**")
                continue

            percentage_guessed = player.get_percentage_guessed(game.word)
            won = math.ceil(percentage_guessed / 100 * bet_pool)

            if len(players) > 1 and i == 0:
                next_won = math.ceil(players[i + 1].get_percentage_guessed(game.word) / 100 * bet_pool)
                if won > next_won:
                    name += " 🌟"

            letters_guessed = player.correct_guesses

            player.identity.add_points(won)
            lines.append(f"{name}\nWon {GOLD_EMOJI}** {won}** ({letters_guessed}/{total_letters}) guessed")
            i += 1

        definition = game.word_definition
        embed.add_field(name=game.unedited_word, value=(definition or "no definition"), inline=False)

        embed.description = "\n\n".join(lines)

        await self.ctx.send(embed=embed)
