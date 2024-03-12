import asyncio
import io
import itertools
import json
import random
import string
from typing import Optional, List, Dict, Union, Callable

import discord

from src import constants
from src.config import config
from src.disc.commands.base.stats import ComparingStat, CountableStat, Stat
from src.disc.commands.base.view import BooleanChoice, wait_for_players, DataChoice
from src.disc.commands.muamua.game import Cycler, Deck, Player, Card, card_unicode_raw, Rank, Suit
from src.models.game import GameStat
from src.utils.stats import Winnings, HumanStat


def ai_only():
    return item_validation(lambda _, x: x.all_ai)


def non_ai_only():
    return item_validation(lambda _, x: not x.all_ai)


def item_validation(validation: Callable[[discord.ui.Item, 'GameMenu'], bool]):
    def wrapper(func):
        func.__validation__ = validation
        return func

    return wrapper


def format_single_line(line_data: List[str], separator: str = ' '):
    """
    Formats multiline data all on the same line
    Example:
        List['AB\\nCD', 'EF\\nGH']
    Would return:
        'AB EF\\nCD GH'
    """
    if len(line_data) == 0:
        return ''
    lines = [[] for _ in range(len(line_data[0].splitlines()))]
    for unicode in line_data:
        for i, line in enumerate(unicode.splitlines()):
            lines[i].append(line)
    return '\n'.join([separator.join(x) for x in lines])


class GameOverException(Exception):
    pass


class Stacking:
    def __init__(self, rank: Rank, target: Optional[Player]):
        self.rank = rank
        self.target = target
        self.count = 0

    def to_dict(self):
        return {
            'rank': self.rank.symbol(),
            'target': self.target.short_identifier,
            'count': self.count,
        }


class Notification:
    def __init__(self, message: str, player: Player, round: int):
        self.message = message
        self.player = player
        self.round = round

    def __str__(self):
        return f'message: {self.message}, player: {self.player}, round: {self.round}'

    def __repr__(self):
        return str(self)


class Stats:
    @classmethod
    def longest_stack(cls, amount: int, rank: Rank) -> ComparingStat:
        return ComparingStat('longest_stack', amount, rank,
                             lambda x: f'Longest stack {x.additional.symbol()}: {x.value}')

    @classmethod
    def invalid_reports(cls) -> CountableStat:
        return CountableStat('invalid_reports', lambda x: f'Invalid reports: {x.count}')

    @classmethod
    def valid_reports(cls) -> CountableStat:
        return CountableStat('valid_reports', lambda x: f'Valid reports: {x.count}')

    @classmethod
    def maumau(cls) -> CountableStat:
        return CountableStat('maumau', lambda x: f'Called MauMau: {x.count}')


class GameSettings:
    def __init__(self, initial_cards: int = 5, invalid_report_penalty: int = 5, valid_report_penalty: int = 5):
        self.initial_cards = initial_cards
        self.invalid_report_penalty = invalid_report_penalty
        self.valid_report_penalty = valid_report_penalty


class GameMenu(discord.ui.View):
    def __init__(self, players: List[Player], min_players: int = 2, settings: Optional[GameSettings] = None):
        super(GameMenu, self).__init__()
        self._children_copy = self.children.copy()
        self.timeout = 360
        self.followup: discord.WebhookMessage = None
        self.all_ai = False
        self.report_file_requested = False

        self._settings = settings or GameSettings()
        self._action_spent = False
        self._ai_speed = 0
        self._wait_time = 0
        self._log: List[Notification] = []
        self._stats: Dict[str, Stat] = {}
        self._table_card: Card = None
        self._stacking: Optional[Stacking] = None
        self._reportable_player_with_one_card: Optional[Player] = None
        self._min_players = min_players
        self._overridden_suit: Optional[Suit] = None
        self._first_to_place_nine = None
        self._add_start_card_value = None
        self._snapshots = {'rounds': []}
        self._winner: Optional[Player] = None

        self._fill_with_ai(players)
        self._cycler = Cycler(players)
        self._players: Dict[Union[str, int], Player] = {x.identifier: x for x in players}
        self._deck_multiplier = max(2, int(len(players) / 3))
        self._deck = Deck.standard53() * self._deck_multiplier
        self._load()
        self._save_round_snapshot()

    async def start(self) -> Optional[Player]:
        if self.all_ai:
            await self.start_bot_fight()
        else:
            await self.wait()
        return self._winner

    def get_report_file(self):
        data = json.dumps(self._snapshots, indent=4)
        return discord.File(io.StringIO(data), filename='state.json')

    async def on_timeout(self):
        print('Timed out...')

    def _save_round_snapshot(self):
        fmt = lambda p, c, n: f'{p.short_identifier} -> {c.short_identifier} (current) -> {n.short_identifier}'

        self._snapshots['rounds'].append({
            'table_card': self._table_card.snapshot_str(),
            'last_card_in_deck': self._deck.cards[-1].snapshot_str(),
            'overridden_suit': self._overridden_suit.name if self._overridden_suit else None,
            'stacking': self._stacking.to_dict() if self._stacking else None,
            'order': fmt(self._cycler.get_previous(), self._cycler.current(), self._cycler.get_next()),
            'hands': {x.short_identifier: ','.join([x.snapshot_str() for x in x.hand]) for x in self._players.values()},
        })

    def _add_stat(self, stat: Stat):
        existing = self._stats.get(stat.type)
        if existing is None:
            self._stats[stat.type] = stat
        else:
            existing.combine(stat)

    def _fill_with_ai(self, players: List[Player]):
        self.all_ai = len(players) == 0
        for i in range(self._min_players - len(players)):
            players.append(Player(f'AI{i + 1}'))

    def _load(self):
        self._deck.shuffle()

        for i, player in enumerate(self._players.values()):
            player.short_identifier = string.ascii_uppercase[i]
            player.hand.extend(self._deck.take_cards(self._settings.initial_cards))
            if self._add_start_card_value:
                player.hand.append(Card(self._add_start_card_value, Suit.HEARTS))

        for i, card in enumerate(self._deck.cards):
            if not card.special:
                self._deck.cards.remove(card)
                self._table_card = card
                break

        self._refresh_items()

    def _refresh_items(self, clear_all: bool = False):
        if clear_all:
            self.clear_items()
        for item in self._children_copy:
            func = item.callback.callback
            if hasattr(func, '__validation__') and not func.__validation__(item, self):
                self.remove_item(item)
            elif clear_all:
                self.add_item(item)

    def _get_hand_contents(self, player: Player):
        formatted = format_single_line(list(map(Card.get_unicode, player.hand)))
        return f'```\n{formatted}```'

    def _get_log_contents(self):
        value = []
        length = 0
        for i in range(len(self._log) - 1, -1, -1):
            notification = self._log[i]
            message = f'Round {notification.round} {notification.player or ""}: {notification.message}'
            would_be_length = length + len(message) + 1
            if would_be_length >= (1024 / 2):
                break
            length = would_be_length
            value.insert(0, message)
        return value

    def _get_table_unicode(self):
        if self._overridden_suit is None:
            return self._table_card.get_unicode()
        else:
            return card_unicode_raw(' ', self._overridden_suit.value)

    def get_embed(self):
        embed = discord.Embed(description=f'>>> ```\n{self._get_table_unicode()}```')

        if len(self._log):
            embed.add_field(name='Log', value='\n'.join(self._get_log_contents()), inline=False)

        game_ended = self._winner is not None

        if game_ended and len(self._stats) > 0:
            stats = []
            for stat in self._stats.values():
                stats.append(stat.readable())
            embed.add_field(name='Post game stats', value='\n'.join(stats), inline=False)

        for player in self._cycler.get_full_cycle():
            emoji = '🔴'
            if player == self._cycler.current():
                emoji = '🟢'
            elif player == self._cycler.get_next():
                emoji = '🟠'
            if game_ended:
                emoji = ''

            embed.add_field(name=f'Player {player.display_name()} {emoji}',
                            value=f'{len(player.hand)} cards',
                            inline=False
                            )

        if not game_ended and self._ai_speed > 0:
            embed.set_footer(text=f'AI speed {self._ai_speed}')
        return embed

    def _can_perform_action(self, interaction: discord.Interaction):
        player = self._players.get(interaction.user.id)
        if player is None:
            return False
        return player.identifier == self._cycler.current().identifier

    def _get_stacked_target(self, rank: Rank) -> Optional[Player]:
        if rank == Rank.NINE and self._stacking is None:
            return self._cycler.get_previous()
        return self._cycler.get_next()

    def _use_stacked_special_ability(self) -> int:
        if self._stacking is None:
            return 0

        cards_to_take = 0
        if self._stacking.rank == Rank.SEVEN:
            cards_to_take = 2 * self._stacking.count
        elif self._stacking.rank == Rank.NINE:
            cards_to_take = 1 * self._stacking.count
            self._cycler.set_current(self._first_to_place_nine)
            self._cycler.reverse()
            self._first_to_place_nine = None
        elif self._stacking.rank == Rank.JOKER:
            cards_to_take = 5 * self._stacking.count

        if cards_to_take > 0:
            self._stacking.target.hand.extend(self._deck.take_cards(cards_to_take))
            self._add_stat(Stats.longest_stack(self._stacking.count, self._stacking.rank))
        return cards_to_take

    async def _use_immediate_special_ability(self, interaction, rank: Rank, suit_callback):
        if rank == Rank.ACE:
            self._cycler.get_next().skip_for += 1
        elif rank == Rank.JACK:
            player = self._cycler.current()
            self._overridden_suit: Suit = await suit_callback(interaction, player)
            self._add_notification(f'Suit chosen: {self._overridden_suit.name}', player)
        elif rank == Rank.QUEEN:
            if len(self._players) == 2:
                self._cycler.get_next().skip_for += 1
            else:
                self._add_notification('Reversed direction', self._cycler.current())
                self._cycler.reverse()
        elif rank == Rank.NINE and self._stacking.count == 1:
            self._first_to_place_nine = self._cycler.current()
            self._cycler.reverse()

    def _get_round(self):
        return max(int(self._cycler.cycles / len(self._players)) + 1, 1)

    def _add_notification(self, message: str, player: Player):
        self._log.append(Notification(message, player, self._get_round()))

    def _has_valid_hand(self, player: Player) -> bool:
        return len(self._get_valid_hand(player)) > 0

    def _apply_stacked_cards(self, player: Player, check_hand: bool = True) -> bool:
        if not self._stacking:
            return False

        if not check_hand or not self._has_valid_hand(player):
            cards_given = self._use_stacked_special_ability()
            self._add_notification(f'+{cards_given} cards', self._stacking.target)
            target = self._stacking.target
            self._stacking = None
            return target == player

    async def _should_skip_player(self, player: Player) -> bool:
        if player.skip_for > 0:
            if player.skip_for > 1:
                self._add_notification(f'Skipped ({player.skip_for - 1} more skips remaining)', player)
            else:
                self._add_notification('Skipped', player)
            player.skip_for -= 1
            return True

        return self._apply_stacked_cards(player)

    async def _choose_suit(self, interaction, _: Player) -> Suit:
        view = DataChoice(list(Suit),
                          to_select=lambda x: discord.SelectOption(label=f'{x.name} ({x.value})', value=x.value))

        await interaction.followup.send(content="Choose a suit", ephemeral=True, wait=True, view=view)
        await view.wait()
        return view.get_first_or_none() or random.choice(list(Suit))

    async def _choose_ai_suit(self, _, player: Player) -> Suit:
        best_suit = None
        highest = 0
        count = {}
        for card in player.hand:
            val = count.setdefault(card.suit, 0) + 1
            count[card.suit] = val
            if val > highest:
                best_suit = card.suit
                highest = val

        return best_suit or list(Suit)

    def _ai_report_cycle(self):
        invalid_report = False

        if random.randint(0, len(self._players) * 65) < 3:
            invalid_report = True
        elif random.randint(0, 5) != 2:
            return

        if not invalid_report and self._reportable_player_with_one_card is None:
            return

        ai_players_remaining = []
        for player in self._players.values():
            if player.is_ai() and player != self._reportable_player_with_one_card:
                ai_players_remaining.append(player)

        if len(ai_players_remaining) == 0:
            return

        reporter = random.choice(ai_players_remaining)
        self._report_player(self._reportable_player_with_one_card, reporter)

    async def _decide_ai_interaction(self, player: Player):
        if self._ai_speed == 0:
            await asyncio.sleep(random.uniform(0.5, 2.3))
        filtered_hand = self._get_valid_hand(player)
        if len(filtered_hand) == 0:
            if self._apply_stacked_cards(player):
                return
            card = self._deck.take_card()
            player.hand.append(card)
            self._add_notification('Drew a card', player)
            if card.can_place_on(self._table_card, self._stacking is not None):
                await self._place_card(None, player, card)
        else:
            card = random.choice(filtered_hand)
            await self._place_card(None, player, card)
            if len(player.hand) == 1 and random.randint(0, 3) == 1:
                self._call_mau_mau(player)

    async def _followup(self, **kwargs):
        await self.followup.edit(**kwargs)

    async def _end_game(self, winner: Player):
        self._winner = winner
        self._add_notification('Wins the game!', winner)
        await self._followup(content=f"Game ended, {winner} won", embed=self.get_embed(), view=None)
        self.stop()

    async def on_error(self, interaction, error: Exception, item) -> None:
        if not isinstance(error, GameOverException):
            await super().on_error(interaction, error, item)

    async def _update_ui(self):
        if self.all_ai and self._ai_speed > 0 and self._cycler.cycles % (self._ai_speed * 3) != 0:
            return
        await self._followup(embed=self.get_embed(), view=self)

    async def _post_player(self, player: Player):
        self._save_round_snapshot()
        player.picking = False
        if len(player.hand) == 0:
            await self._end_game(player)
            raise GameOverException()
        self._ai_report_cycle()
        await self._update_ui()

        if self._wait_time > 0:
            await asyncio.sleep(self._wait_time)
            self._wait_time = 0

        self._action_spent = False
        self._cycler.next()
        await self._update_ui()

    async def _post_interaction(self):
        if not self.all_ai:
            await self._post_player(self._cycler.current())

        while self._winner is None:
            skipped = False
            if await self._should_skip_player(self._cycler.current()):
                await self._post_player(self._cycler.current())
                skipped = True
            if self._cycler.current().is_ai():
                await self._decide_ai_interaction(self._cycler.current())
                await self._post_player(self._cycler.current())
                skipped = True
            if not skipped:
                break

    async def start_bot_fight(self):
        if self.all_ai:
            try:
                await self._post_interaction()
            except GameOverException:
                pass

    def _get_valid_hand(self, player: Player) -> List[Card]:
        if self._overridden_suit:
            return [x for x in player.hand if x.suit == self._overridden_suit or x in (Rank.JOKER, Rank.JACK)]
        return [x for x in player.hand if x.can_place_on(self._table_card, self._stacking is not None)]

    def _stack(self, rank: Rank):
        if self._stacking is None:
            self._stacking = Stacking(rank, self._get_stacked_target(rank))
        else:
            self._stacking.target = self._get_stacked_target(rank)
        self._stacking.count += 1

    async def _place_card(self, interaction, player: Player, card: Card):
        self._add_notification(f'Placed {card}', player)

        if card.stackable:
            self._stack(card.rank)

        if card.special:
            callback = self._choose_ai_suit if player.is_ai() else self._choose_suit
            await self._use_immediate_special_ability(interaction, card.rank, callback)
        if card.rank != Rank.JACK:
            self._overridden_suit = None
        self._deck.add_card_at_random_position(card)
        self._table_card = card
        player.hand.remove(card)

        self._reportable_player_with_one_card = None
        if len(player.hand) == 1:
            self._reportable_player_with_one_card = player
            self._set_wait_time(5)
        else:
            self._set_wait_time(3)

    def _set_wait_time(self, time: int):
        if not self.all_ai:
            self._wait_time = time

    def _call_mau_mau(self, player: Player):
        self._add_stat(Stats.maumau())
        self._reportable_player_with_one_card = None
        self._add_notification('MAU MAU!!', player)

    def _report_player(self, player: Player, reporter: Player):
        if player is None:
            c = self._settings.invalid_report_penalty
            self._add_notification(f'You waste the MauMau authorities time and resources with an invalid report.'
                                   f' They let you off with a slap on the wrist this time... +{c} cards.', reporter)
            reporter.hand.extend(self._deck.take_cards(self._settings.invalid_report_penalty))
            self._add_stat(Stats.invalid_reports())
        else:
            c = self._settings.valid_report_penalty
            self._add_notification(f'The MauMau authorities received an anonymous tip by {reporter} '
                                   f'that someone forgot to call MauMau, +{c} cards.', player)
            player.hand.extend(self._deck.take_cards(self._settings.valid_report_penalty))
            self._add_stat(Stats.valid_reports())
            self._reportable_player_with_one_card = None

    @non_ai_only()
    @discord.ui.button(label='Draw', style=discord.ButtonStyle.gray, emoji='🫴')
    async def draw(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self._can_perform_action(interaction):
            await interaction.response.defer()
            return

        player: Player = self._players[interaction.user.id]
        if self._apply_stacked_cards(player, check_hand=False):
            await self._post_interaction()
            return

        self._action_spent = True
        card = self._deck.take_card()
        player.hand.append(card)
        responded = False
        self._add_notification('Drew a card', player)
        if card.can_place_on(self._table_card, self._stacking is not None):
            view = BooleanChoice(False)
            await interaction.response.send_message(f"You drew the {card} card. Place it right away?",
                                                    ephemeral=True, view=view)
            responded = True
            await view.wait()
            if view.value:
                await self._place_card(interaction, player, card)
        if not responded:
            await interaction.response.send_message(self._get_hand_contents(player), ephemeral=True)

        await self._post_interaction()

    @non_ai_only()
    @discord.ui.button(label='Place', style=discord.ButtonStyle.green, emoji='🫳')
    async def place(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self._can_perform_action(interaction):
            await interaction.response.defer()
            return

        player: Player = self._players[interaction.user.id]

        filtered_hand = self._get_valid_hand(player)
        if len(filtered_hand) == 0:
            await interaction.response.send_message("No cards", ephemeral=True)
            return

        cont = itertools.count()
        view = DataChoice(filtered_hand,
                          lambda x: discord.SelectOption(label=str(x),
                                                         value=str(next(cont)),
                                                         description=x.ability_description))
        await interaction.response.send_message(constants.BR, view=view, ephemeral=True)
        await view.wait()

        if self._cycler.current().identifier != interaction.user.id:
            await interaction.followup.send("Wtf", ephemeral=True)
            return

        if self._action_spent:
            await interaction.followup.send("You rat", ephemeral=True)
            return

        self._action_spent = True
        card = view.get_first_or_none()

        if card is None:
            if not self._apply_stacked_cards(player):
                self._add_notification('Timed out, taking card...', player)
                player.hand.append(self._deck.take_card())
            await self._post_interaction()
            return

        await self._place_card(interaction, player, card)
        await self._post_interaction()

    @non_ai_only()
    @discord.ui.button(label='Show hand', style=discord.ButtonStyle.gray, emoji='✋')
    async def show(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self._players.get(interaction.user.id)
        if player is None:
            await interaction.response.defer()
            return
        await interaction.response.send_message(self._get_hand_contents(player), ephemeral=True)

    @non_ai_only()
    @discord.ui.button(label='MauMau', style=discord.ButtonStyle.blurple, emoji='‼️')
    async def maumau(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self._players[interaction.user.id]
        if player is None or self._reportable_player_with_one_card is None:
            await interaction.response.defer()
            return
        if self._reportable_player_with_one_card == player:
            self._call_mau_mau(player)
        await interaction.response.defer()

    @non_ai_only()
    @discord.ui.button(label='Report MauMau', style=discord.ButtonStyle.red, emoji='🚔')
    async def report_maumau(self, interaction: discord.Interaction, _button: discord.ui.Button):
        reporter = self._players.get(interaction.user.id)
        if reporter is None:
            await interaction.response.defer()
            return

        self._report_player(self._reportable_player_with_one_card, reporter)
        await self._update_ui()
        await interaction.response.defer()

    @discord.ui.button(label='Bug report', style=discord.ButtonStyle.gray, emoji='🐛')
    async def bug_report(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.report_file_requested = True
        await interaction.response.send_message("Okay, at the end of the game I'll send a debug file")

    @ai_only()
    @discord.ui.button(label='Speed up', style=discord.ButtonStyle.gray, emoji='🤖')
    async def speedup(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self._ai_speed += 1
        await interaction.response.defer()

    def _remove_player(self, player: Player):
        self._cycler.remove(player)
        del self._players[player.identifier]
        self._add_notification('Left the game', player)

    @non_ai_only()
    @discord.ui.button(label='Leave', style=discord.ButtonStyle.red, emoji='🚪')
    async def leave(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self._players[interaction.user.id]
        if player is None:
            await interaction.response.defer()
            return

        self._remove_player(player)

        if len(self._players) == 1:
            await self._end_game(self._cycler.current())
            await interaction.response.send_message(f'You forfeit the match, leaving {self._winner} as the winner')
            return

        self.all_ai = all(x.is_ai() for x in self._players.values())
        if self.all_ai:
            self._refresh_items(clear_all=True)
            await interaction.response.send_message("Removing you from the game caused the game to become a bot fight.")
            await self.start_bot_fight()
        else:
            await interaction.response.send_message("I've removed you from the game.")
            await self._update_ui()


@config.tree.command(name="maumau", description="Play MauMau")
async def maumau(interaction: discord.Interaction, min_players: Optional[int] = 2):
    user_ids = await wait_for_players(interaction)
    menu = GameMenu([Player(x, member=interaction.guild.get_member(x)) for x in user_ids], min_players)
    menu.followup = await interaction.followup.send(embed=menu.get_embed(), wait=True, view=menu)

    winner = await menu.start()
    if winner is None:
        await interaction.followup.send('No one wins, no one loses.')
    elif not winner.is_ai():
        stat, _ = GameStat.get_or_create(key='maumau_wins', user_id=winner.member.id)
        stat.value = str(int(stat.value) + 1)
        winnings = Winnings(HumanStat.gold(random.randint(5, 15)))
        await interaction.followup.send(f'Congrats <@{winner.member.id}>, you now have a total of {stat.value} wins'
                                        f'.\nYou won {winnings.format()}')
        stat.save()

    if menu.report_file_requested:
        await interaction.followup.send(file=menu.get_report_file())


@config.tree.command(name="maumau_scoreboard",
                     description="Check out the MauMau scoreboard (sponsored by the MauMau authorities)")
async def maumau_scoreboard(interaction: discord.Interaction):
    values = list(GameStat.select().where(GameStat.key == 'maumau_wins'))
    values.sort(key=lambda x: int(x.value), reverse=True)
    messages = [f'<@{x.user_id}>: {x.value}' for x in values]
    await interaction.response.send_message('\n'.join(messages))
