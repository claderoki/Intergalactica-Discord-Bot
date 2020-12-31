import asyncio
from enum import Enum
import math

import discord 

from .ui import UI

class DiscordUI(UI):
    def __init__(self, ctx):
        self.message = None
        self.ctx = ctx

    def __check(self, word, letters_used, player):
        def __check2(message):
            if not self.ctx.channel.id == message.channel.id:
                return False
            if not player.identity.member.id == message.author.id:
                return False
            if len(message.content) == len(word):
                return True
            if len(message.content) == 1:
                letter = message.content.lower()
                asyncio.gather(message.delete())
                if letter not in letters_used:
                    return True
                else:
                    asyncio.gather(self.ctx.error(f"Letter '{letter}' has already been used", delete_after = 10))

            return False
        return __check2

    async def get_guess(self, word, player, letters_used):
        try:
            guess = await self.ctx.bot.wait_for("message", check = self.__check(word, letters_used, player) )
        except asyncio.TimeoutError:
            guess = None

        return guess.content.lower() if guess is not None else None

    async def refresh_board(self, game, current_player = None):
        embed = discord.Embed(color = self.ctx.guild_color, title=" ".join(game.board))

        for player in game.players:
            if player.dead:
                continue

            length = len(str(player))

            # arrows = "`" + (((length // 2) - 1) * " ") + "↑`"
            arrows = ""

            embed.add_field(
                name = str(player),
                value = f"```\n{self.game_states[player.incorrect_guesses]}```" + (arrows if player == current_player else "") )

        guess_info = []
        guess_info.append("letters used: " + ", ".join(game.letters_used))
        guess_info.append("words used: " + ", ".join(game.words_used))
        if current_player is not None:
            guess_info.append(f"{current_player.identity.member.mention}s turn")

        embed.add_field(name = "\uFEFF", value = "\n".join(guess_info), inline = False)

        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
        else:
            await self.message.edit(embed=embed)

    async def stop(self, reason, game):
        embed = discord.Embed(title = f"Game has ended: {reason.value}", color = self.ctx.guild_color)
        lines = []

        bet_pool = sum([x.bet for x in game.players])
        bet_pool *= 1.25
        bet_pool += (15 * len(game.players))
        bet_pool = int(bet_pool)

        for player in game.players:
            if player.dead:
                player.identity.remove_points(player.bet)
                lines.append(f"{player.identity.member.mention} lost **{player.bet}** gold")
            else:
                percentage_guessed = player.get_percentage_guessed(game.word)
                won = math.ceil(percentage_guessed / 100 * bet_pool)
                player.identity.add_points(won)
                lines.append(f"{player.identity.member.mention} won **{won}** gold ({int(percentage_guessed)}%)")

        embed.description = "\n".join(lines)
        embed.set_footer(text = f"word: {game.word}")

        await self.ctx.send(embed = embed)
