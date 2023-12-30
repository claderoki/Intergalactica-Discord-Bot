import asyncio
import time
import random
from typing import Optional, List, Dict

import discord
# import peewee

import src.config as config
from src.discord.commands.muamua.game import Cycler, Deck, Player, Card, MauTrack


class JoinMenu(discord.ui.View):
    def __init__(self):
        super(JoinMenu, self).__init__()
        self.user_ids = set()

    def __get_content(self):
        return "\n".join(map(str, self.user_ids))

    @discord.ui.button(label='Join', style=discord.ButtonStyle.red)
    async def join(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.user_ids.add(interaction.user.id)
        await interaction.response.edit_message(content=self.__get_content(), view=self)

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.user_ids.remove(interaction.user.id)
        await interaction.response.edit_message(content=self.__get_content(), view=self)

    @discord.ui.button(label='Start', style=discord.ButtonStyle.red)
    async def start(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.stop()
        await interaction.response.defer()


class CardSelect(discord.ui.Select):
    def __init__(self, cards: List[Card]):
        super().__init__(
            placeholder='Choose a card',
            min_values=1,
            max_values=1,
            options=[self.__card_to_option(i, x) for i, x in enumerate(cards)])
        self.selected = None
        self.cards = cards

    @staticmethod
    def __card_to_option(index: int, card: Card):
        return discord.SelectOption(label=str(card), value=str(index), description=card.ability_description)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected = self.cards[int(self.values[0])]
        self.view.stop()


class CardChoice(discord.ui.View):
    def __init__(self, cards: List[Card]):
        super(CardChoice, self).__init__()
        self.add_item(CardSelect(cards))

    def get_selected(self) -> Optional[Card]:
        return self.children[0].selected


class DataSelect(discord.ui.Select):
    def __init__(self, data: list, to_select):
        self.data = {}
        options = []
        for x in data:
            select = to_select(x)
            self.data[select.value] = x
            options.append(select)
        super().__init__(min_values=1, max_values=1, options=options)
        self.selected = []

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected = [self.data[x] for x in self.values]
        self.view.stop()


class DataChoice(discord.ui.View):
    def __init__(self, data: list, to_select):
        super(DataChoice, self).__init__()
        self.add_item(DataSelect(data, to_select))

    def get_selected(self) -> list:
        return self.children[0].selected


class BooleanChoice(discord.ui.View):
    def __init__(self, default: bool = False):
        super(BooleanChoice, self).__init__()
        self.value = default

    options = [discord.SelectOption(label='Yes'), discord.SelectOption(label='No')]

    @discord.ui.select(placeholder='Choose', min_values=1, max_values=1, options=options)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = select.values[0] == 'Yes'
        await interaction.response.defer()
        self.stop()


class SuitChoice(discord.ui.View):
    def __init__(self):
        super(SuitChoice, self).__init__()
        self.value = None

    options = [discord.SelectOption(label=x.name, value=x.value) for x in Card.Suit]

    @discord.ui.select(placeholder='Choose', min_values=1, max_values=1, options=options)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = Card.Suit(select.values[0])
        await interaction.response.defer()
        self.stop()


class Stacking:
    def __init__(self, rank: str, target: Optional[Player]):
        self.rank = rank
        self.target = target
        self.count = 0


class Notification:
    def __init__(self, message: str, player: Player, round: int):
        self.message = message
        self.player = player
        self.round = round


class GameMenu(discord.ui.View):
    def __init__(self, players: List[Player]):
        super(GameMenu, self).__init__()
        self.timeout = 2000
        self.all_ai = False
        self.notifications = []
        self.players_mau: Dict[str, float] = {}
        self.followup = None
        self.stacking: Optional[Stacking] = None
        self.table_card = None
        self.min_players = 2
        self.overriden_suit: Card.Suit = None
        self.__fill_with_ai(players)
        self.cycler = Cycler(players)
        self.players: Dict[str, Player] = {x.identifier: x for x in players}
        self.deck = Deck.standard53()
        self.__load()

    async def on_timeout(self):
        print('Timed out...')

    def __fill_with_ai(self, players: List[Player]):
        self.all_ai = len(players) == 0
        for i in range(self.min_players - len(players)):
            players.append(Player(f'AI{i + 1}'))

    def __load(self):
        self.deck.shuffle()

        for player in self.players.values():
            player.hand.extend(self.deck.take_cards(5))

        for i, card in enumerate(self.deck.cards):
            if not card.special:
                self.deck.cards.remove(card)
                self.table_card = card
                break

    def card_unicode_raw(self, rank, symbol):
        spaces = " " if len(rank) == 1 else ""
        lines = []
        lines.append("┌─────┐")
        lines.append(f"│{rank}{spaces}   │")
        lines.append(f"│{symbol}   {symbol}│")
        lines.append(f"│   {spaces}{rank}│")
        lines.append("└─────┘")
        unicode = "\n".join(lines)
        return unicode.replace("┌", "╭").replace("┐", "╮").replace("┘", "╯").replace("└", "╰")

    def card_unicode(self, card):
        return self.card_unicode_raw(card.rank, card.symbol)

    def get_hand_contents(self, player: Player):
        unicodes = list(map(self.card_unicode, player.hand))
        lines = [[] for _ in range(len(unicodes[0].splitlines()))]
        for unicode in unicodes:
            for i, line in enumerate(unicode.splitlines()):
                lines[i].append(line)

        c = "\n".join([" ".join(x) for x in lines])
        return f'```\n{c}```'

    def get_embed(self):
        embed = discord.Embed(description=self.get_content())
        for player in self.players.values():
            embed.add_field(name="Player " + str(player.member or player.identifier),
                            value=f"{len(player.hand)} cards",
                            inline=False
                            )
        return embed

    def get_content(self):
        content = []

        if self.overriden_suit is None:
            unicode = self.card_unicode(self.table_card)
        else:
            unicode = self.card_unicode_raw(' ', self.overriden_suit.value)

        content.append('>>> ```\n' + unicode + '```')
        content.append(f'{self.cycler.current()}')

        if len(self.notifications):
            content.append('Notifications')
        for notification in self.notifications:
            round = int(self.cycler.cycles / len(self.players)) + 1
            if notification.round > round - 3:
                content.append(f'Round {notification.round} {notification.player}: {notification.message}')

        return '\n'.join(content)

    def is_allowed(self, interaction: discord.Interaction):
        player = self.players.get(interaction.user.id)
        if player is None:
            return False
        return player.identifier == self.cycler.current().identifier

    def __get_stacked_target(self, rank: str) -> Optional[Player]:
        if rank == '7' or rank == '*':
            return self.cycler.get_next()
        elif rank == '9':
            return self.cycler.get_previous()

    def __use_stacked_special_ability(self) -> int:
        if self.stacking is None:
            return 0

        cards_to_take = 0
        if self.stacking.rank == '7':
            cards_to_take = 2 * self.stacking.count
        elif self.stacking.rank == '9':
            cards_to_take = 1 * self.stacking.count
        elif self.stacking.rank == '*':
            cards_to_take = 5 * self.stacking.count

        if cards_to_take > 0:
            self.stacking.target.hand.extend(self.deck.take_cards(cards_to_take))
        return cards_to_take

    async def __use_immediate_special_ability(self, interaction, rank: str, suit_callback):
        if rank == 'A':
            self.cycler.get_next().skip_for += 1
        elif rank == 'J':
            player = self.cycler.current()
            self.overriden_suit = await suit_callback(interaction, player)
            self.__add_notification('Suit chosen: ' + self.overriden_suit.name, player)
        elif rank == 'Q':
            if len(self.players) == 2:
                self.cycler.get_next().skip_for += 1
            else:
                self.__add_notification('Reversed direction', self.cycler.current())
                self.cycler.reverse()

    def __add_notification(self, message: str, player: Player):
        round = int(self.cycler.cycles / len(self.players)) + 1
        self.notifications.append(Notification(message, player, round))

    def __apply_stacked_cards(self, player: Player, force: bool = False) -> bool:
        if self.stacking and (force or len(self.__get_valid_hand(player)) == 0):
            cards_given = self.__use_stacked_special_ability()
            self.__add_notification(f'+{cards_given} cards', self.stacking.target)
            target = self.stacking.target
            self.stacking = None
            return target == player
        return False

    async def __should_skip_player(self, player: Player) -> bool:
        if player.skip_for > 0:
            if player.skip_for > 1:
                self.__add_notification(f'Skipped ({player.skip_for - 1} more skips remaining)', player)
            else:
                self.__add_notification('Skipped', player)
            player.skip_for -= 1
            return True

        return self.__apply_stacked_cards(player)

    async def __choose_suit(self, interaction, _: Player) -> Card.Suit:
        view = SuitChoice()
        await interaction.followup.send(content="Choose a suit", ephemeral=True, wait=True, view=view)
        await view.wait()
        return view.value or random.choice(list(Card.Suit))

    async def __choose_ai_suit(self, _, player: Player) -> Card.Suit:
        best_suit = None
        highest = 0

        count = {}
        for card in player.hand:
            val = count.setdefault(card.suit, 0) + 1
            count[card.suit] = val
            if val > highest:
                best_suit = card.suit
                highest = val

        return best_suit

    def __ai_report_cycle(self):
        if random.randint(0, 5) != 2:
            return
        players = [x for x in self.players.values() if x.last_mau is not None and self.__can_report_mau_mau(x, self.__current_mau_track())]
        if len(players) == 0:
            return
        ai_players_remaining = [x for x in self.players.values() if x.is_ai() and x not in players]
        if len(ai_players_remaining) == 0:
            return
        reporter = random.choice(ai_players_remaining)
        player = random.choice(players)
        self.__report_player(player, reporter)

    async def __decide_ai_interaction(self, player: Player):
        await asyncio.sleep(random.uniform(0.5, 2.3))
        filtered_hand = self.__get_valid_hand(player)
        if len(filtered_hand) == 0:
            if not self.__apply_stacked_cards(player, force=False):
                card = self.deck.take_card()
                player.hand.append(card)
                self.__add_notification('Drew a card', player)
                if card.can_place_on(self.table_card, self.stacking is not None):
                    # todo: may not always want to place the card depending on the hand.
                    await self.__place_card(None, player, card, self.__choose_ai_suit)
            return
        await self.__place_card(None, player, random.choice(filtered_hand), self.__choose_ai_suit)
        if len(player.hand) == 1:
            if random.randint(0, 3) == 1:
                self.__call_mau_mau(player)

    async def __followup(self, **kwargs):
        await self.followup.edit(**kwargs)

    async def __end_game(self, winner: Player):
        await self.__followup(content="Game ended, " + str(winner) + ' won', embed=self.get_embed(),
                              view=self)
        self.stop()

    async def __update(self):
        await self.__followup(embed=self.get_embed(), view=self)

    async def __post_interaction(self):
        if len(self.cycler.current().hand) == 0:
            return await self.__end_game(self.cycler.current())

        # if self.all_ai and self.cycler.cycles != 0:
        self.__ai_report_cycle()
        self.cycler.next()

        while True:
            skipped = False
            if await self.__should_skip_player(self.cycler.current()):
                if len(self.cycler.current().hand) == 0:
                    return await self.__end_game(self.cycler.current())

                self.__ai_report_cycle()
                self.cycler.next()
                await self.__update()
                skipped = True
            if self.cycler.current().is_ai():
                await self.__decide_ai_interaction(self.cycler.current())
                if len(self.cycler.current().hand) == 0:
                    return await self.__end_game(self.cycler.current())

                self.__ai_report_cycle()
                self.cycler.next()
                await self.__update()
                skipped = True
            if not skipped:
                break

        await self.__update()

    def __get_valid_hand(self, player: Player):
        if self.overriden_suit:
            return [x for x in player.hand if x.suit == self.overriden_suit]
        return [x for x in player.hand if x.can_place_on(self.table_card, self.stacking is not None)]

    async def __place_card(self, interaction, player: Player, card: Card, suit_callback=None):
        self.__add_notification('Placed ' + str(card), player)
        if suit_callback is None:
            suit_callback = self.__choose_suit
        if card.stackable:
            if self.stacking is None:
                self.stacking = Stacking(card.rank, self.__get_stacked_target(card.rank))
            if card.rank != '9':
                self.stacking.target = self.__get_stacked_target(card.rank)
            self.stacking.count += 1
        elif card.special:
            await self.__use_immediate_special_ability(interaction, card.rank, suit_callback)
        if card.rank != 'J':
            self.overriden_suit = None
        self.deck.add_card_at_random_position(card)
        self.table_card = card
        player.hand.remove(card)
        if len(player.hand) == 1:
            player.last_mau = self.__current_mau_track()

    @discord.ui.button(label='Draw', style=discord.ButtonStyle.red)
    async def draw(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self.is_allowed(interaction):
            await interaction.response.defer()
            return

        player: Player = self.players[interaction.user.id]
        if self.__apply_stacked_cards(player, force=False):
            await self.__post_interaction()
            return

        card = self.deck.take_card()
        player.hand.append(card)
        responded = False
        self.__add_notification('Drew a card', player)
        if card.can_place_on(self.table_card, self.stacking is not None):
            view = BooleanChoice(False)
            await interaction.response.send_message(f"You drew the {card} card. Place it right away?",
                                                    ephemeral=True, view=view)
            responded = True
            await view.wait()
            if view.value:
                await self.__place_card(interaction, player, card)

        if not responded:
            await interaction.response.send_message(self.get_hand_contents(player), ephemeral=True)

        await self.__post_interaction()

    @discord.ui.button(label='Place', style=discord.ButtonStyle.red)
    async def place(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self.is_allowed(interaction):
            await interaction.response.defer()
            return

        player: Player = self.players[interaction.user.id]

        filtered_hand = self.__get_valid_hand(player)
        if len(filtered_hand) == 0:
            await interaction.response.send_message("No cards", ephemeral=True)
            return

        view = CardChoice(filtered_hand)
        await interaction.response.send_message("_", view=view, ephemeral=True)
        await view.wait()
        card = view.get_selected()
        if card is None:
            if not self.__apply_stacked_cards(player, force=False):
                self.__add_notification('Timed out, taking card...', player)
                player.hand.append(self.deck.take_card)
            await self.__post_interaction()
            return

        await self.__place_card(interaction, player, card)
        await self.__post_interaction()

    @discord.ui.button(label='Show hand', style=discord.ButtonStyle.red)
    async def show(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self.players.get(interaction.user.id)
        if player is None:
            await interaction.response.defer()
        await interaction.response.send_message(self.get_hand_contents(player), ephemeral=True)

    def __current_mau_track(self) -> MauTrack:
        return MauTrack(time.time(), self.cycler.cycles)

    def __call_mau_mau(self, player: Player):
        player.last_mau = None
        self.__add_notification('MAU MAU!!', player)

    def __can_call_mau_mau(self, player: Player, current: MauTrack = None) -> bool:
        current = current or self.__current_mau_track()
        print('diff', current.time - player.last_mau.time)
        return current.time - player.last_mau.time < 10

    def __can_report_mau_mau(self, player: Player, current: MauTrack = None) -> bool:
        current = current or self.__current_mau_track()
        if self.__can_call_mau_mau(player, current):
            return False
        return (current.time - player.last_mau.time) < 40

    @discord.ui.button(label='MauMau', style=discord.ButtonStyle.red)
    async def maumau(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self.players[interaction.user.id]
        if player is None or player.last_mau is None:
            await interaction.response.defer()
            return

        if self.__can_call_mau_mau(player):
            self.__call_mau_mau(player)

    def __report_player(self, player: Player, reporter: Player):
        self.__add_notification(f'The MauMau authorities received an anonymous tip by {reporter} '
                                f'that someone forgot to call MauMau, +5 cards.', player)
        player.hand.extend(self.deck.take_cards(5))
        player.last_mau = None

    def __get_mau_players(self, current: Player):
        return [x for x in self.players.values() if x.identifier != current.identifier and x.last_mau is not None]

    @discord.ui.button(label='Report MauMau', style=discord.ButtonStyle.red)
    async def report_maumau(self, interaction: discord.Interaction, _button: discord.ui.Button):
        reporter = self.players.get(interaction.user.id)
        if reporter is None:
            await interaction.response.defer()
            return

        players = self.__get_mau_players(reporter)
        if len(players) == 0:
            await interaction.response.defer()
            return

        current = self.__current_mau_track()

        view = DataChoice(players, lambda x: discord.SelectOption(label=str(x.identifier, x.member.display_name)))
        await interaction.response.send_message(f"Boom", ephemeral=True, view=view)
        await view.wait()
        player = view.get_selected()[0]
        if self.__can_report_mau_mau(player, current):
            self.__report_player(player, reporter)

    @discord.ui.button(label='BOT FIGHT', style=discord.ButtonStyle.red)
    async def botfight(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()
        if self.cycler.cycles == 0:
            await self.__post_interaction()

#
# @config.tree.command(name="maumau",
#                      description="My first application Command",
#                      guild=discord.Object(id=761624318291476482))
# async def first_command(interaction):
#     menu = JoinMenu()
#     await interaction.response.send_message("_", view=menu)
#     await menu.wait()
#
#     menu = GameMenu([Player(x) for x in menu.user_ids])
#     if menu.all_ai:
#         menu.children.clear()
#     menu.followup = await interaction.followup.send(embed=menu.get_embed(), wait=True, view=menu)
#
#     await menu.wait()
