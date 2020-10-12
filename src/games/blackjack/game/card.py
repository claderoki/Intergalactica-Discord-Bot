from enum import Enum

class Card:
    class Suits(Enum):
        spades   = "♠"
        clubs    = "♣"
        hearts   = "♥"
        diamonds = "♦"

    _ranks = {1:"A", 11:"J",12:"Q",13:"K"}

    def __init__(self, value, suit, hidden = False):
        self.value  = value
        self.suit   = suit
        self.hidden = hidden

        self._unicode = None

        self.symbol = suit.value

        self.rank = self._ranks.get(self.value, str(self.value))

    @property
    def score(self):
        if self.hidden:
            return 0
        else:
            return self.value if self.value < 11 else 10
