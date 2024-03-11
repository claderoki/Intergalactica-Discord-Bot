import string
from typing import List, Optional

from src.disc.commands import Rank, Suit, GameOverException
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

    async def draw(self, card: Optional[Card] = None, place_immediately=True):
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

    async def place(self, rank: Rank, suit: Suit):
        player = self._cycler.current()
        await self._place_card(None, player, self.get_card(rank, suit))
        await self._post_interaction()


async def test1():
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

    await menu.draw()  # P1
    await menu.place(Rank.SEVEN, Suit.HEARTS)  # P2
    try:
        await menu.place(Rank.JACK, Suit.HEARTS)  # P2 (P1 skipped)
        print('failed')
    except GameOverException:
        print('success')
