import random
from .card import Card

class Deck:
    def __init__(self):
        self.cards = []

        for i in range(1,14):
            self.cards.append(Card(i, Card.Suits.hearts))

        for i in range(1,14):
            self.cards.append(Card(i, Card.Suits.diamonds))

        for i in range(1,14):
            self.cards.append(Card(i, Card.Suits.spades))

        for i in range(1,14):
            self.cards.append(Card(i, Card.Suits.clubs))

    def shuffle(self):
        random.shuffle(self.cards)

    def take_card(self, hidden = False):
        card = self.cards.pop()
        card.hidden = hidden
        return card
