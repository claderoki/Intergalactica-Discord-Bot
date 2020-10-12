import random
import asyncio

import discord
import emoji

from .ui import UI
from src.discord.helpers.waiters import ReactionWaiter

class DiscordUI(UI):
    def __init__(self, ctx):
        self.ctx = ctx
        self.message = None

    async def draw_or_stand(self, player):
        if player.type == player.Type.ai:
            await asyncio.sleep(0.5)
            return player.Action.draw

        draw_emoji   = "✅"
        stand_emoji  = "❌" 

        waiter = ReactionWaiter(self.ctx, self.message, emojis = (draw_emoji, stand_emoji), channels = [self.ctx.channel], members = [self.ctx.author])
        await waiter.add_reactions()
        emoji = await waiter.wait()

        if emoji == draw_emoji:
            return player.Action.draw
        else:
            return player.Action.stand

    async def display_board(self, game, current_player = None):

        embed = discord.Embed(
            title = f">>> Dealer ({game.dealer.score})",
            description = self.get_player_cards_unicode(game.dealer),
            color=self.ctx.guild_color
        )

        for player in game.players:
            name = []
            name.append(">>> ")

            name.append(f"{player.identity} ({player.type.value})")

            value = []
            value.append(self.get_player_cards_unicode(player))
            if player == current_player:
                symbol = "▶️"
            elif player.state == player.State.bust:
                symbol = "⏹️"
            else:
                symbol = "⏸️"

            value.append(f"(**{player.score}**) - {player.state.name.title()} {symbol}")

            if game.done:
                amount_won = player.amount_won
                if amount_won != 0:
                    value.append(f"\n{player.state.value}{player.state.name.title()}")
                    abc = "won" if amount_won > 0 else "lost"
                    value.append(f"{abc} {abs(amount_won)}")



            embed.add_field(
                name = "".join(name),
                value = "".join(value),
                inline = True
            )

        if self.message is None:
            self.message = await self.ctx.channel.send(embed = embed)
        else:
            await self.message.edit(embed = embed)



    def get_player_cards_unicode(self, player, hidden = False):
        cards_as_str = ">>> ```\n"
        # cards_as_str = ">>> "

        ascii_lines = 5
        for i in range(ascii_lines):
            for card in player.cards:
                if hidden:
                    unicode = self.cards_hidden_unicode
                else:
                    unicode = self.card_unicode(card)

                if card == player.cards[-1]:
                    cards_as_str += unicode.splitlines()[i]
                else:
                    cards_as_str += unicode.splitlines()[i][:3]
            cards_as_str += "\n"

        return cards_as_str + "```"

    async def game_over(self, game):
        try:
            await self.message.clear_reactions()
        except:
            pass
        await self.display_board(game)
        # game_over_lines = ["```"]

        # for player in game.players:
        #     game_over_lines.append(
        #         f"{player.identity}: {player.state.name} - " + \
        #         ("won " if player.amount_won > 0 else "lost ") + str(abs(player.amount_won)))

        # game_over_lines.append("```")

        # await self.message.channel.send("\n".join(game_over_lines))
