from .ui import UI
import emoji
import discord

class DiscordUI(UI):
    numbers = [emoji.emojize(f":keycap_{i}:") for i in range(1,10)]

    def __init__(self, ctx):
        self.ctx = ctx
        self.message = None

    async def get_move(self, board, player):
        emoji = await self.ctx.wait_for_emoji(self.message,
            author        = player.member,
            emojis        = (self.numbers),
            check         = lambda r,u : board[self.numbers.index(str(r.emoji))+1] == " ",
            remove_after  = True)

        if emoji is not None:
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
