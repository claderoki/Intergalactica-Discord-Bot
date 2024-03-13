import string
import unittest
from typing import List, Optional

from src.disc.commands import Rank, Suit, GameOverException, Cycler
from src.disc.commands.muamua import Deck, Card, Player, GameMenu, GameSettings


class TestGameMenu(GameMenu):
    def __init__(self, players: List[Player], deck: Deck, table_card: Card):
        self._test_deck = deck
        self._test_table_card = table_card
        super().__init__(players=players, min_players=0, settings=GameSettings(initial_cards=1))

    async def _update_ui(self):
        pass

    async def _followup(self, **kwargs):
        pass

    def stop(self):
        pass

    async def _choose_suit(self, _, player: Player) -> Suit:
        return Suit.HEARTS

    def _set_wait_time(self, time: int):
        pass

    def _load(self):
        self._table_card = self._test_table_card
        self._deck = self._test_deck
        for i, player in enumerate(self._players.values()):
            player.short_identifier = string.ascii_uppercase[i]

    async def draw_card(self, card: Optional[Card] = None, place_immediately=True):
        player = self._cycler.current()
        card = card or self._deck.take_card()
        player.hand.append(card)
        if card.can_place_on(self._table_card, self._stacking is not None) and place_immediately:
            await self._place_card(None, player, card)
        await self._post_interaction()

    def get_card(self, rank: Rank, suit: Suit):
        player = self._cycler.current()
        for card in player.hand:
            if card.rank == rank and card.suit == suit:
                return card

    async def place_card(self, rank: Rank, suit: Suit, suit_if_j: Suit = None):
        player = self._cycler.current()
        await self._place_card(None, player, self.get_card(rank, suit))
        await self._post_interaction()


class MauMauTest(unittest.IsolatedAsyncioTestCase):
    async def test1(self):
        deck = Deck('', [
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.JOKER, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.THREE, Suit.CLUBS),
            Card(Rank.FIVE, Suit.DIAMONDS),
        ])

        p1 = Player(1)
        p2 = Player(2)

        menu = TestGameMenu([p1, p2], deck, table_card=Card(Rank.TWO, Suit.HEARTS))

        p1.hand.extend([
            Card(Rank.FIVE, Suit.DIAMONDS),
            Card(Rank.EIGHT, Suit.CLUBS),
        ])
        p2.hand.extend([
            Card(Rank.SEVEN, Suit.HEARTS),
            Card(Rank.JACK, Suit.HEARTS),
        ])

        await menu.draw_card()  # P1
        await menu.place_card(Rank.SEVEN, Suit.HEARTS)  # P2
        with self.assertRaises(GameOverException):
            await menu.place_card(Rank.JACK, Suit.HEARTS)  # P2 (P1 skipped)

    async def test2(self):
        deck = Deck('', [Card(Rank.TWO, Suit.DIAMONDS)])

        p1 = Player(1)
        p2 = Player(2)

        menu = TestGameMenu([p1, p2], deck, table_card=Card(Rank.TWO, Suit.HEARTS))

        p1.hand.extend([Card(Rank.SEVEN, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS)])
        p2.hand.extend([Card(Rank.EIGHT, Suit.DIAMONDS), Card(Rank.TEN, Suit.DIAMONDS)])

        await menu.place_card(Rank.SEVEN, Suit.HEARTS)
        await menu.draw_card()
        await menu.place_card(Rank.JACK, Suit.CLUBS)
        await menu.place_card(Rank.TWO, Suit.DIAMONDS)
        await menu.place_card(Rank.TEN, Suit.DIAMONDS)
        await menu.place_card(Rank.NINE, Suit.DIAMONDS)


def test_cycler():
    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    cycler.next()
    assert cycler.current() == 'C'
    cycler.remove(cycler.get_previous())
    assert cycler.current() == 'C'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    assert cycler.current() == 'B'
    cycler.remove(cycler.current())
    assert cycler.current() == 'C'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    assert cycler.current() == 'B'
    cycler.remove(cycler.current())
    assert cycler.current() == 'C'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    assert cycler.current() == 'A'
    cycler.remove(cycler.get_next())
    assert cycler.current() == 'A'
    assert cycler.get_next() == 'C'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    cycler.reverse()
    assert cycler.current() == 'B'
    cycler.remove(cycler.current())
    assert cycler.current() == 'A'
    assert cycler.get_next() == 'D'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    cycler.next()
    cycler.reverse()
    assert cycler.current() == 'C'
    cycler.remove(cycler.get_next())
    assert cycler.current() == 'C', 'current is ' + cycler.current() + ' instead'
    assert cycler.get_next() == 'A'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    cycler.next()
    cycler.reverse()
    assert cycler.current() == 'C'
    cycler.remove(cycler.get_next())
    assert cycler.current() == 'C', 'current is ' + cycler.current() + ' instead'
    assert cycler.get_next() == 'A'

    cycler = Cycler(['A', 'B', 'C', 'D'])
    cycler.next()
    cycler.reverse()
    assert cycler.current() == 'B'
    cycler.remove(cycler.current())
    assert cycler.current() == 'A', 'current is ' + cycler.current() + ' instead'
    assert cycler.get_next() == 'D'


async def te():
    while True:
        code = GameTestCodeGenerator()
        await code.start_bot_fight()
        if code._cycler.cycles < 10:
            break
    print('\n\n'.join(code.code))


class GameTestCodeGenerator(GameMenu):
    def __init__(self, initial=2):
        super().__init__(players=[], settings=GameSettings(initial_cards=initial))
        self.code = []
        self._ai_speed = 5
        self.used_deck = []

        v = []
        for i, p in enumerate(self._players.values()):
            i += 1
            self.code.append(f'p{i} = Player({i})')
            v.append(f'p{i}')
        self.code.append(
            f'menu = TestGameMenu([{",".join(v)}], deck, table_card={self._card_constructor(self._table_card)})')

        for i, p in enumerate(self._players.values()):
            i += 1
            self.code.append(f'p{i}.hand.extend({self._cards_list(p.hand)})')

    async def _update_ui(self):
        pass

    async def _followup(self, **kwargs):
        pass

    def stop(self, **kwargs):
        self.code.insert(0, f"deck = Deck('', {self._cards_list(self.used_deck)})")

    def _card_params(self, card: Card):
        return f'Rank.{card.rank.name}, Suit.{card.suit.name if card.suit else None}'

    def _card_constructor(self, card: Card):
        return f'Card({self._card_params(card)})'

    def _cards_list(self, cards: List[Card]):
        return '[' + (','.join([self._card_constructor(x) for x in cards])) + ']'

    def _draw_card(self, player: Player) -> Card:
        c = super()._draw_card(player)
        self.code.append(f'await menu.draw_card()')
        self.used_deck.append(c)
        return c

    async def _place_card(self, interaction, player: Player, card: Card):
        await super()._place_card(interaction, player, card)
        self.code.append(f'await menu.place_card({self._card_params(card)})')
