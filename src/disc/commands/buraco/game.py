import abc
import random
from enum import Enum
from typing import List, TypeVar, Generic, Union, Optional, Dict


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


class CardList(abc.ABC):
    def __init__(self, cards: List['Card']):
        self.cards = cards

    def __str__(self):
        return str(cards)

    def __repr__(self):
        return str(cards)


class CardSequence(CardList):
    def __init__(self, cards: List['Card']):
        super().__init__(cards)


class Hand(CardList):
    def __init__(self, cards: List['Card']):
        super().__init__(cards)

    def reorganise(self) -> List['CardSequence']:
        organised: Dict[Suit, List[Card]] = {}
        for card in self.cards:
            organised.setdefault(card.suit, []).append(card)

        for cards in organised.values():
            cards.sort(key=lambda x: x.rank.value, reverse=False)
        print(self.cards, organised, '\n')
        return [CardSequence(x) for x in organised.values()]


class Card:
    _ability_desc = {
        Rank.JOKER: 'Next player 5 cards',
        Rank.ACE: "Skip next persons turn",
        Rank.SEVEN: 'Next player 2 cards',
        Rank.NINE: 'Previous player 1 card',
        Rank.JACK: "Choose new suit",
        Rank.QUEEN: "Reverses order"
    }

    def __init__(self, rank: Rank, suit: Optional[Suit]):
        self.rank = rank
        self.suit = suit

        self._symbol = suit.value if suit else None

        self.ability_description = self._ability_desc.get(self.rank)
        self.special = self.ability_description is not None
        self.stackable = self.rank in (Rank.SEVEN, Rank.NINE, Rank.JOKER)

    def can_place_on(self, card: 'Card', stacking: bool = False) -> bool:
        """card: card to place be placed on."""
        if stacking:
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
        return f'{self.rank.symbol()} {self._symbol or ""}'

    def snapshot_str(self):
        if not self.suit:
            return self.rank.symbol()
        return f'{self.rank.symbol()} {self.suit.name}'

    def __repr__(self):
        return str(self)

    def copy(self) -> 'Card':
        return Card(self.rank, self.suit)

    def get_unicode(self):
        return card_unicode_raw(self.rank.symbol(), self._symbol)


class Deck(CardList):
    __slots__ = ('cards', 'name', '_infinite')

    def __init__(self, name: str, cards: List[Card]):
        super().__init__(cards)
        self.name = name
        self._infinite = False

    @classmethod
    def standard52(cls):
        cards = []
        for suit in Suit:
            for i in range(1, 14):
                cards.append(Card(Rank(i), suit))
        return cls('Standard 52', cards)

    @classmethod
    def standard53(cls):
        deck = cls.standard52()
        deck.cards.append(Card(Rank.JOKER, None))
        return cls('Standard 53', deck.cards)

    @classmethod
    def standard54(cls):
        deck = cls.standard52()
        deck.cards.append(Card(Rank.JOKER, None))
        deck.cards.append(Card(Rank.JOKER, None))
        return cls('Standard 54', deck.cards)

    def infinite(self):
        """Sets infinite to True, making it impossible to not have cards."""
        self._infinite = True
        return self

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
        if self.infinite and len(self.cards) == 0:
            self.combine(self.copy())
        return self.cards.pop()

    def take_cards(self, amount: int) -> List[Card]:
        return [self.take_card() for _ in range(amount)]

    def add_card_at_random_position(self, card: Card):
        index = random.randint(0, len(self.cards))
        self.cards.insert(index, card)


class Player:
    __slots__ = ('identifier', 'hand', 'skip_for', 'member',
                 'last_mau', 'picking', 'short_identifier', 'is_ai', 'points')

    def __init__(self, identifier: Union[str, int], member=None, is_ai: bool = False):
        self.identifier = identifier
        self.member = member
        self.hand: List[Card] = []
        self.is_ai = is_ai
        self.points = -200
        self.short_identifier: str = None
        self.skip_for = 0
        self.picking = False

    def __str__(self):
        if self.is_ai:
            return self.identifier
        return f'<@{self.identifier}>'

    def display_name(self):
        return str(self) if self.member is None else self.member.display_name


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

    def _next_index(self):
        if self.current_index >= len(self.items) - 1:
            return 0
        else:
            return self.current_index + 1

    def _previous_index(self):
        if self.current_index <= 0:
            return len(self.items) - 1
        else:
            return self.current_index - 1

    def _get_next_item(self, seek: bool) -> T:
        index = self._next_index() if self.forwards else self._previous_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def _get_previous_item(self, seek: bool) -> T:
        index = self._previous_index() if self.forwards else self._next_index()
        if seek:
            self.current_index = index
        return self.items[index]

    def get_next(self) -> T:
        return self._get_next_item(False)

    def get_previous(self) -> T:
        return self._get_previous_item(False)

    def current(self) -> T:
        return self.items[self.current_index]

    def next(self) -> T:
        self.cycles += 1
        return self._get_next_item(True)

    def previous(self) -> T:
        self.cycles += 1
        return self._get_previous_item(True)

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

    def remove(self, item: T):
        if item not in self.items:
            return

        removed_index = self.items.index(item)
        if self.forwards:
            if removed_index < self.current_index:
                self.current_index -= 1
        else:
            if removed_index >= self.current_index:
                self.current_index = self._previous_index()
            else:
                self.current_index -= 1

        self.items.remove(item)


if __name__ == '__main__':
    cards = [
        Card(Rank.JOKER, None),
        Card(Rank.NINE, Suit.DIAMONDS),
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.FOUR, Suit.DIAMONDS),
        Card(Rank.FIVE, Suit.DIAMONDS),

        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.TWO, Suit.HEARTS),
        Card(Rank.THREE, Suit.HEARTS),
        Card(Rank.FIVE, Suit.HEARTS),
    ]

    seq = Hand(cards)
    print(seq.reorganise())
