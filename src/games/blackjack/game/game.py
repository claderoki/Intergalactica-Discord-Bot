from src.games.blackjack.ui.ui import UI
from src.games.blackjack.ui.discord_ui import DiscordUI

from .player import Player
from .deck import Deck
from src.games.game.base import BaseGame

class Game(BaseGame):

    def __init__(self, players, ui : UI):
        assert isinstance(ui, UI)

        self.ui = ui
        self.done = False
        self.deck = Deck()
        self.deck.shuffle()

        self.dealer = Player(None, name = "Dealer")
        self.dealer.draw(self.deck)
        self.dealer.draw(self.deck, hidden = True)

        self.players = players

        for player in self.players:
            player.draw(self.deck)
            player.draw(self.deck)

            if player.score == 21 and len(player.cards) == 2:
                player.state = player.State.blackjack

    @property
    def players_done(self):
        for player in self.players:
            if not player.done:
                return False

        return True

    def calculate_state(self, player):
        score        = player.score
        if score == 21 and len(player.cards) == 2:
            player.state = player.State.blackjack
        elif score > 21:
            player.state = player.State.bust

    def calculate_end_state(self, player):
        score        = player.score
        dealer_score = self.dealer.score

        if dealer_score > 21 and score < 21:
            player.state = player.State.win
        elif score == dealer_score:
            player.state = player.State.draw
        elif score == 21 and len(player.cards) == 2:
            player.state = player.State.blackjack
        elif score > 21:
            player.state = player.State.lose
        elif score > dealer_score:
            player.state = player.State.win
        else:
            player.state = player.State.lose

    async def stop(self):
        pass

    async def start(self):
        while not self.players_done:
            for player in self.players:
                if player.done:
                    continue

                await self.ui.display_board(self, player)

                player_action = await self.ui.draw_or_stand(player)

                if player_action == Player.Action.stand:
                    player.state = Player.State.stand
                else:
                    player.draw(self.deck)
                    self.calculate_state(player)

        await self.ui.display_board(self)
        self.done = True

        for card in self.dealer.cards:
            card.hidden = False

        while self.dealer.score < 17:
            self.dealer.draw(self.deck)

        for player in self.players:
            self.calculate_end_state(player)

        await self.ui.game_over(self)