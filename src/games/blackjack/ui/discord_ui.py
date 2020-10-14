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

        waiter = ReactionWaiter(
            self.ctx,
            self.message,
            emojis = (draw_emoji, stand_emoji),
            channels = [self.ctx.channel],
            members = [self.ctx.author],
        )
        await waiter.add_reactions()
        try:
            emoji = await waiter.wait(timeout = 120, remove = True)
        except asyncio.TimeoutError:
            emoji = draw_emoji

        if emoji == draw_emoji:
            return player.Action.draw
        else:
            return player.Action.stand

    def get_player_value(self, player, game):
        return self.get_players_cards_emoji(player)

    def get_player_name(self, player, game):
        value = []
        value.append(f"{player.identity}")
        value.append("\n")
        value.append(f"{self.ctx.translate('card_value')} = **{player.score}**")
        if game.done:
            amount_won = player.amount_won
            if amount_won:
                value.append(f"\n{self.ctx.translate(player.state.name)}")
                abc = "won" if amount_won > 0 else "lost"
                abc = self.ctx.translate(abc)
                value.append(f", {abc} {abs(amount_won)}")
        return "".join(value)

    async def display_board(self, game, current_player = None):
        embed = discord.Embed(
            title = self.get_player_name(game.dealer, game),
            description = self.get_player_value(game.dealer, game),
            color=self.ctx.guild_color
        )

        for player in game.players:
            embed.add_field(
                name = self.get_player_name(player, game),
                value = self.get_player_value(player, game),
                inline = True
            )

        if self.message is None:
            self.message = await self.ctx.channel.send(embed = embed)
        else:
            await self.message.edit(embed = embed)

    def get_players_cards_emoji(self, player, hidden = False):
        emojis = []
        for card in player.cards:
            if card.hidden or hidden:
                emoji = str(self.ctx.bot._emoji_mapping["hidden_card"])
            else:
                value = card.value if card.value != 13 else 12
                emoji = str(self.ctx.bot._emoji_mapping[f"{card.suit.name}_{value}" ])
            emojis.append(emoji)
        return "".join(emojis)

    def get_player_cards_unicode(self, player, hidden = False):
        cards_as_str = ">>> ```\n"
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