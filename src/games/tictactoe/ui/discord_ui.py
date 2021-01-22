import asyncio

import emoji
import discord

from .ui import UI

class DiscordUI(UI):
    numbers = [emoji.emojize(f":keycap_{i}:") for i in range(1,10)]

    def __init__(self, ctx):
        self.ctx = ctx
        self.message = None

    def __check(self, player, board):
        def __check2(reaction, user):
            if user.id != player.identity.member.id:
                return False
            emoji = str(reaction.emoji)
            if emoji not in self.numbers:
                return False
            index = self.numbers.index(emoji)
            if board[index+1] != " ":
                return False

            return True
        return __check2

    async def get_move(self, board, player):
        try:
            emoji, user = await self.ctx.bot.wait_for("reaction_add", timeout = 60, check = self.__check(player, board))
        except asyncio.TimeoutError:
            return None
        else:
            return self.numbers.index(str(emoji))+1

    async def show_board(self, game, player):
        board = game.board
        view = """
 {} ┃ {} ┃ {}
━━━┣━━━╋━━━
 {} ┃ {} ┃ {}
━━━┣━━━╋━━━
 {} ┃ {} ┃ {}
        """.format(*board[1:])


        embed = discord.Embed(title = "Tictactoe",
            description = "\n".join([f"{x.symbol}: {x}" for x in game.players]),
            color=discord.Color.red())

        embed.add_field(name = "Board", value = f"```\n{view}```")

        embed.set_footer(text = f"{player}s turn")

        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
            if not game.ai_only:
                for emoji in self.numbers:
                    await self.message.add_reaction(emoji)
        else:
            await self.message.edit(embed=embed)

    async def game_over(self, winner):
        try:
            await self.message.clear_reactions()
        except: pass

        if winner is None:
            await self.ctx.send("Game is a draw!")
        else:
            await self.ctx.send(f"Game over, winner: {winner}")
