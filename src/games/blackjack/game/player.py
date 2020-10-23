from enum import Enum

from src.games.game.base import BasePlayer
from src.games.game.base import DiscordIdentity, AiIdentity


class Player(BasePlayer):

    class Type(Enum):
        human  = "🧑"
        ai     = "🤖"

    class State(Enum):
        bust      = 1
        draw      = 2
        blackjack = "🎆"
        stand     = 4
        drawing   = 5
        win       = "👍"
        lose      = "👎"

    class Action(Enum):
        stand = 1
        draw  = 2

    def __init__(self, bet, member = None, name = None):
        if member is None:
            identity = AiIdentity(name = name or "AI")
            self.type = self.Type.ai

        else:
            identity = DiscordIdentity(member)
            self.type = self.Type.human

        super().__init__(identity = identity)

        self.bet = bet

        self.cards = []
        self.state = self.State.drawing

    @property
    def amount_won(self):
        if self.bet is None:
            return

        return {
            self.State.bust:       -self.bet,
            self.State.draw:       0,
            self.State.blackjack:  self.bet * 4,
            self.State.win:        self.bet * 2,
            self.State.lose:       -self.bet
        }[self.state]

    @property
    def done(self):
        return self.state != self.State.drawing

    @property
    def score(self):
        total_score = 0 

        aces = 0

        for card in self.cards:
            if card.score != 1:
                total_score += card.score
            else:
                aces += 1

        for _ in range(aces):
            if (total_score + 11) > 21:
                total_score += 1
            else:
                total_score += 11 

        if total_score == 21:
            self.state == self.State.blackjack
        elif total_score > 21:
            self.state = self.State.bust

        return total_score


    def draw(self, deck, hidden = False):
        self.cards.append(deck.take_card(hidden))
