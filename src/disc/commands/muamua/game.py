import random
from enum import Enum
from typing import List, TypeVar, Generic, Union


def card_unicode_raw(rank, symbol):
    symbol = symbol or ' '
    spaces = ' ' if len(rank) == 1 else ''
    lines = [f'╭─────╮',
             f'│{rank}{spaces}   │',
             f'│{symbol}   {symbol}│',
             f'│   {spaces}{rank}│',
             f'╰─────╯']
    return '\n'.join(lines)


class Suit(Enum):
    SPADES = '♠'
    CLUBS = '♣'
    HEARTS = '♥'
    DIAMONDS = '♦'


class Rank(Enum):
    JOKER = -1
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    def symbol(self) -> str:
        if self == self.JOKER:
            return '*'
        if self == self.ACE:
            return 'A'
        if self == self.JACK:
            return 'J'
        if self == self.QUEEN:
            return 'Q'
        if self == self.KING:
            return 'K'
        return str(self.value)


class Card:

    _ability_desc = {
        Rank.JOKER: 'Next player 5 cards',
        Rank.ACE: "Skip next persons turn",
        Rank.SEVEN: 'Next player 2 cards',
        Rank.NINE: 'Previous player 1 card',
        Rank.JACK: "Choose new suit",
        Rank.QUEEN: "Reverses order"
    }

    def __init__(self, rank: Rank, suit):
        self.rank = rank
        self.suit = suit
        self._rank_symbol = self.rank.symbol()

        self._symbol = suit.value if suit else None

        self.ability_description = self._ability_desc.get(self.rank)
        self.special = self.ability_description is not None
        self.stackable = self.rank in (Rank.SEVEN, Rank.NINE, Rank.JOKER)

    def can_place_on(self, card: 'Card', stacking: bool = False) -> bool:
        if stacking and card.stackable:
            return card.rank == self.rank

        if self.rank == Rank.JOKER or card.rank == Rank.JOKER:
            return True
        if self.rank == Rank.JACK:
            return True
        same_rank = card.rank == self.rank
        if card.suit == self.suit or same_rank:
            return True
        return False

    def __str__(self):
        return f'{self._rank_symbol} {self._symbol or ""}'

    def snapshot_str(self):
        if not self.suit:
            return self._rank_symbol
        return f'{self._rank_symbol} {self.suit.name}'

    def __repr__(self):
        return str(self)

    def copy(self) -> 'Card':
        return Card(self.rank, self.suit)

    def get_unicode(self):
        return card_unicode_raw(self._rank_symbol, self._symbol)


class Deck:
    __slots__ = ('cards', 'name')

    def __init__(self, name: str, cards: List[Card]):
        self.name = name
        self.cards = cards

    @classmethod
    def standard52(cls):
        cards = []
        for suit in Suit:
            for i in range(1, 14):
                cards.append(Card(Rank(i), suit))
        return cls('Standard 52', cards)

    @classmethod
    def standard53(cls):
        cards = []
        for suit in Suit:
            for i in range(1, 14):
                cards.append(Card(Rank(i), suit))

        cards.append(Card(Rank.JOKER, None))
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

    def get_full_cycle(self):
        """
        Gets the full cycle of the cycler, where the first item is the current item.
        Does not modify self.cycles or changes the index.
        """
        current = self.current_index
        if self.forwards:
            initial = range(current, len(self.items))
            second = range(0, current)
            order = list(initial) + list(second)
        else:
            initial = range(current, -1, -1)
            second = range(len(self.items) - 1, current, -1)
            order = list(initial) + list(second)
        return [self.items[x] for x in order]
