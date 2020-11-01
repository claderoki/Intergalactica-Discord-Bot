from enum import Enum
import math

import discord 

from .ui import UI

class DiscordUI(UI):



    def __init__(self, ctx):
        self.message = None
        self.ctx = ctx


    async def get_guess(self, word, player, letters_used):

        # guess = await self.ctx.wait_for_message(
        #     channel = self.ctx.channel,
        #     author = str(player),
        #     check = lambda m : (len(m.content) == 1 or len(m.content) == len(word) and m.content.lower() not in letters_used ))

        try:
            await guess.delete()
        except: pass

        return guess.content.lower() if guess is not None else None


    async def refresh_board(self, game, current_player = None):

        embed = discord.Embed(title=" ".join(game.board))

        for player in game.players:
            if player.dead:
                continue

            length = len(str(player))

            arrows = "`" + (((length // 2) - 1) * " ") + "↑`"

            embed.add_field(
                name = str(player),
                value = f"```\n{self.game_states[player.incorrect_guesses]}```" + (arrows if player == current_player else "") )



        guess_info = []
        guess_info.append("letters used: " + ", ".join(game.letters_used))
        guess_info.append("words used: " + ", ".join(game.words_used))

        embed.add_field(name = "\uFEFF", value = "\n".join(guess_info), inline = False)

        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
        else:
            await self.message.edit(embed=embed)


    async def stop(self, reason, game):
        lines = ["Game has ended."]
        lines.append(reason.value)

        bet_pool = sum([x.bet for x in game.players])
        bet_pool = int(bet_pool * 1.25)

        for player in game.players:
            if player.dead:
                player.identity.remove_points(player.bet)
                lines.append(f"Player {player} has lost **{player.bet}** gold")

            else:

                percentage_guessed = player.get_percentage_guessed(game.word)

                won = math.ceil(percentage_guessed / 100 * bet_pool)

                player.identity.add_point(won)

                lines.append(f"Player {player} has won **{won}** gold, percentage guessed: **{int(percentage_guessed)}**")

        lines.append(f"The word was {game.word}")

        await self.ctx.send("\n".join(lines))
