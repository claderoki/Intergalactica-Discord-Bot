import random
from enum import Enum
from typing import List, TypeVar, Generic, Union


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
        self.symbol = suit.value if suit else None
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
        return f'{self.rank} {self.symbol if self.symbol is not None else ""}'

    def snapshot_str(self):
        #todo: fix
        return f'{self.rank} {self.suit.name[0] if self.suit else ""}'.strip()

    def __repr__(self):
        return str(self)

    def copy(self) -> 'Card':
        return Card(self.value, self.suit)


class Deck:
    __slots__ = ('cards', 'name')

    def __init__(self, name: str, cards: List[Card]):
        self.name = name
        self.cards = cards

    @classmethod
    def standard52(cls):
        cards = []
        for suit in Card.Suit:
            for i in range(1, 14):
                cards.append(Card(i, suit))
        return cls('Standard 52', cards)

    @classmethod
    def standard53(cls):
        cards = []
        for suit in Card.Suit:
            for i in range(1, 14):
                cards.append(Card(i, suit))

        cards.append(Card(15, None))
        return cls('Standard 53', cards)

    def __mul__(self, other):
        if other != 1:
            for i in range(0, other):
                self.combine(self.copy())
        return self

    def copy(self) -> 'Deck':
        return Deck(self.name, [x.copy() for x in self.cards])

    def combine(self, deck: 'Deck'):
        self.cards.extend(deck.cards)

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
    __slots__ = ('identifier', 'hand', 'skip_for', 'member', 'last_mau', 'picking', 'short_identifier')

    def __init__(self, identifier: Union[str, int], member=None):
        self.identifier = identifier
        self.member = member
        self.hand: List[Card] = []
        self.short_identifier: str = None
        self.skip_for = 0
        self.picking = False

    def __str__(self):
        if self.is_ai():
            return self.short_identifier
        return f'<@{self.identifier}>'

    def display_name(self):
        return str(self) if self.member is None else self.member.display_name

    def is_ai(self):
        return 'AI' in str(self.identifier)


T = TypeVar('T')


class Cycler(Generic[T]):
    __slots__ = ('items', 'forwards', 'current_index', 'cycles')

    def __init__(self, items: List[T], forwards: bool = True):
        self.items = items
        self.forwards = forwards
        self.cycles = 0
        self.current_index = 0

    def reverse(self):
        self.forwards = not self.forwards

    def set_current(self, item: T):
        self.current_index = self.items.index(item)

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

    def __get_next_item(self, seek: bool) -> T:
        index = self.__next_index() if self.forwards else self.__previous_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def __get_previous_item(self, seek: bool) -> T:
        index = self.__previous_index() if self.forwards else self.__next_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def get_next(self) -> T:
        return self.__get_next_item(False)

    def get_previous(self) -> T:
        return self.__get_previous_item(False)

    def current(self) -> T:
        return self.items[self.current_index]

    def next(self) -> T:
        self.cycles += 1
        return self.__get_next_item(True)

    def previous(self) -> T:
        self.cycles += 1
        return self.__get_previous_item(True)
