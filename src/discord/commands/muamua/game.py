import random
from enum import Enum
from typing import List


# class Rank(Enum):
#     A = 1
#     2 = 2

class Card:
    class Suit(Enum):
        spades = "♠"
        clubs = "♣"
        hearts = "♥"
        diamonds = "♦"

    _ranks = {1: "A", 11: "J", 12: "Q", 13: "K", 15: '*'}

    _ability_desc = {1: "Skip next persons turn",
                     11: "Choose new suit",
                     12: "Reverses order",
                     7: 'Next player 2 cards',
                     9: 'Previous player 1 card',
                     15: 'Next player 5 cards'}

    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        self.symbol = suit.value if suit else ''
        self.ability_description = self._ability_desc.get(self.value, None)
        self.rank = self._ranks.get(self.value, str(self.value))
        self.special = self.rank in ('A', '7', '9', 'J', 'Q', '*')
        self.stackable = self.rank in ('7', '9', '*')

    def can_place_on(self, card: 'Card', stacking: bool = False) -> bool:
        if stacking and card.stackable:
            return card.rank == self.rank

        if self.rank == '*' or card.rank == '*':
            return True
        if self.rank == 'J':
            return True
        same_rank = card.rank == self.rank
        if card.suit == self.suit or same_rank:
            return True
        return False

    def __str__(self):
        return f'{self.rank} {self.symbol}'


class Deck:
    __slots__ = ('cards',)

    def __init__(self, cards: List[Card]):
        self.cards = cards

    @classmethod
    def standard52(cls):
        cards = []
        for suit in Card.Suit:
            for i in range(1, 14):
                cards.append(Card(i, suit))
        return cls(cards)

    @classmethod
    def standard53(cls):
        cards = []
        for suit in Card.Suit:
            for i in range(1, 14):
                cards.append(Card(i, suit))

        cards.append(Card(15, None))
        return cls(cards)

    def shuffle(self):
        random.shuffle(self.cards)

    def take_card(self):
        return self.cards.pop()

    def take_cards(self, amount: int) -> List[Card]:
        return [self.take_card() for _ in range(amount)]

    def add_card_at_random_position(self, card: Card):
        index = random.randint(0, len(self.cards))
        self.cards.insert(index, card)


class MauTrack:
    def __init__(self, time: float, cycles: int):
        self.time = time
        self.cycles = cycles


class Player:
    __slots__ = ('identifier', 'hand', 'skip_for', 'member', 'last_mau')

    def __init__(self, identifier: str, member=None):
        self.identifier = identifier
        self.member = member
        self.hand: List[Card] = []
        self.skip_for = 0
        self.last_mau = None

    def __str__(self):
        if self.is_ai():
            return self.identifier
        return f'<@{self.identifier}>'

    def is_ai(self):
        return 'AI' in str(self.identifier)

    def mau(self, mau_track: MauTrack):
        self.last_mau = mau_track


class Cycler:
    __slots__ = ('items', 'forwards', 'current_index', 'cycles')

    def __init__(self, items: list, forwards: bool = True):
        self.items = items
        self.forwards = forwards
        self.cycles = 0
        self.current_index = 0

    def reverse(self):
        self.forwards = not self.forwards

    def __next_index(self):
        if self.current_index >= len(self.items) - 1:
            return 0
        else:
            return self.current_index + 1

    def __previous_index(self):
        if self.current_index <= 0:
            return len(self.items) - 1
        else:
            return self.current_index - 1

    def __get_next_item(self, seek: bool):
        index = self.__next_index() if self.forwards else self.__previous_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def __get_previous_item(self, seek: bool):
        index = self.__previous_index() if self.forwards else self.__next_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def get_next(self):
        return self.__get_next_item(False)

    def get_previous(self):
        return self.__get_previous_item(False)

    def current(self):
        return self.items[self.current_index]

    def next(self):
        self.cycles += 1
        return self.__get_next_item(True)

    def previous(self):
        self.cycles += 1
        return self.__get_previous_item(True)