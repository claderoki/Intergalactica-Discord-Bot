import random
from typing import Optional, List

import discord
# import peewee

import src.config as config
from src.discord.commands.muamua.game import Cycler, Deck, Player, Card
from src.models.personalroles import PersonalRoleSettings


#
# class ModelEditSettings:
#     def __init__(self, field: peewee.Field, required: bool = False):
#         self.field = field
#         self.required = required
#
#
# class ModelEditor:
#     def __init__(self, model: peewee.Model, settings: list):
#         self.model = model
#
#
# def abc():
#     ModelEditor(PersonalRoleSettings(), [
#         ModelEditSettings(PersonalRoleSettings.required_role_id, required=False)
#     ])


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
            options=[discord.SelectOption(label=str(x), value=i, description=x.ability_description) for i, x in
                     enumerate(cards)])
        self.selected = None
        self.cards = cards

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


class BooleanSelect(discord.ui.Select):
    def __init__(self, default: bool = False):
        super().__init__(
            placeholder='Choose',
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label='Yes', value=1),
                discord.SelectOption(label='No', value=0),
            ])
        self.value = default

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = int(self.values[0]) == 1
        self.view.stop()


class BooleanChoice(discord.ui.View):
    def __init__(self, default: bool = False):
        super(BooleanChoice, self).__init__()
        self.add_item(BooleanSelect(default))

    def get_value(self) -> bool:
        return self.children[0].value


class Stacking:
    def __init__(self, rank: str, target: Optional[Player]):
        self.rank = rank
        self.target = target
        self.count = 0


class Notification:
    def __init__(self, message: str, player: Player = None):
        self.message = message
        self.player = player


class GameMenu(discord.ui.View):
    def __init__(self, players: List[Player]):
        super(GameMenu, self).__init__()
        self.notifications = []
        self.stacking: Optional[Stacking] = None
        self.table = []
        self.overriden_suit = None
        self.__fill_with_ai(players)
        self.cycler = Cycler(players)
        self.players = {x.identifier: x for x in players}
        self.deck = Deck.standard53()
        self.__load()

    def __fill_with_ai(self, players: List[Player]):
        for i in range(2 - len(players)):
            players.append(Player(f'AI{i + 1}'))

    def __load(self):
        self.deck.shuffle()

        for player in self.players.values():
            player.hand.extend(self.deck.take_cards(5))

        for i, card in enumerate(self.deck.cards):
            if not card.special:
                self.deck.cards.remove(card)
                self.table.append(card)
                break

    def card_unicode(self, card):
        spaces = " " if len(card.rank) == 1 else ""
        lines = []
        lines.append("┌─────┐")
        lines.append(f"│{card.rank}{spaces}   │")
        lines.append(f"│{card.symbol}   {card.symbol}│")
        lines.append(f"│   {spaces}{card.rank}│")
        lines.append("└─────┘")
        unicode = "\n".join(lines)
        return unicode.replace("┌", "╭").replace("┐", "╮").replace("┘", "╯").replace("└", "╰")

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
            content.append('```\n' + self.card_unicode(self.table[-1]) + '```')
        else:
            content.append(self.overriden_suit)
        content.append(f'{self.cycler.current()}')

        if len(self.notifications):
            content.append('Notifications')
        for notification in self.notifications:
            if notification.player is None:
                content.append(f'{notification.message}')
            else:
                content.append(f'{notification.player}: {notification.message}')
        # self.notifications.clear()
        return '\n'.join(content)

    def is_allowed(self, interaction: discord.Interaction):
        player = self.players[interaction.user.id]
        return player is not None and player.identifier == self.cycler.current().identifier

    def __get_stacked_target(self, rank: str) -> Optional[Player]:
        if rank == '7' or rank == '*':
            return self.cycler.get_next()
        elif rank == '9':
            return self.cycler.get_previous()

    def __use_stacked_special_ability(self) -> int:
        stacking = self.stacking
        if stacking is None:
            return 0

        before = len(stacking.target.hand)
        if stacking.rank == '7':
            stacking.target.hand.extend(self.deck.take_cards(2 * self.stacking.count))
        elif stacking.rank == '9':
            stacking.target.hand.extend(self.deck.take_cards(1 * self.stacking.count))
        elif stacking.rank == '*':
            stacking.target.hand.extend(self.deck.take_cards(5 * self.stacking.count))
        print('Applying stack...')
        return len(stacking.target.hand) - before

    async def __use_immediate_special_ability(self, rank: str):
        if rank == 'A':
            self.cycler.get_next().skip_for += 1
            print('Skipping', self.cycler.get_next().identifier)
        elif rank == 'J':
            pass  # chooses which suit the next player has to place on the table
        elif rank == 'Q':
            if len(self.players) == 2:
                print('Skipping', self.cycler.get_next().identifier)
                self.cycler.get_next().skip_for += 1
            else:
                self.__add_notification('Reversing...')
                self.cycler.reverse()

    def __add_notification(self, message: str, player: Player = None):
        self.notifications.append(Notification(message, player))

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
            self.__add_notification(f'Skipped ({player.skip_for-1} more skips remaining)', player)
            player.skip_for -= 1
            return True

        return self.__apply_stacked_cards(player)

    async def __decide_ai_interaction(self, player: Player):
        filtered_hand = self.__get_valid_hand(player)
        if len(filtered_hand) == 0:
            if not self.__apply_stacked_cards(player, force=False):
                player.hand.extend(self.deck.take_cards(1))
                self.__add_notification('Drew a card', player)
            return
        await self.__place_card(player, random.choice(filtered_hand))

    async def __followup(self, **kwargs):
        await self.followup.edit(**kwargs)

    async def __post_interaction(self):
        if len(self.cycler.current().hand) == 0:
            await self.__followup(content="GAME FINISHED", embed=self.get_embed(), view=self)
            self.stop()
            return

        self.cycler.next()

        while True:
            skipped = False
            if await self.__should_skip_player(self.cycler.current()):
                self.cycler.next()
                skipped = True
            if self.cycler.current().is_ai():
                await self.__decide_ai_interaction(self.cycler.current())
                self.cycler.next()
                skipped = True
            if not skipped:
                break

        await self.__followup(embed=self.get_embed(), view=self)

    def __get_valid_hand(self, player: Player):
        if self.stacking:
            return [x for x in player.hand if x.rank == self.table[-1].rank]
        if self.overriden_suit:
            return [x for x in player.hand if x.suit == self.overriden_suit]
        return [x for x in player.hand if x.can_place_on(self.table[-1])]

    async def __place_card(self, player: Player, card: Card):
        if card.stackable:
            if self.stacking is None:
                self.stacking = Stacking(card.rank, self.__get_stacked_target(card.rank))
            if card.rank != '9':
                self.stacking.target = self.__get_stacked_target(card.rank)
            self.stacking.count += 1
        elif card.special:
            await self.__use_immediate_special_ability(card.rank)
        self.table.append(card)
        if card.rank != 'J':
            self.overriden_suit = None
        player.hand.remove(card)
        self.__add_notification('Placed ' + str(card), player)

    @discord.ui.button(label='Draw', style=discord.ButtonStyle.red)
    async def draw(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self.is_allowed(interaction):
            await interaction.response.defer()
            return

        player: Player = self.players[interaction.user.id]
        if not self.__apply_stacked_cards(player, force=False):
            card = self.deck.take_card()
            player.hand.append(card)
            responded = False
            self.__add_notification('Drew a card', player)
            if card.can_place_on(self.table[-1]):
                view = BooleanChoice(False)
                await interaction.response.send_message(f"You drew the {card} card. Place it right away?", ephemeral=True, view=view)
                responded = True
                await view.wait()
                if view.get_value():
                    await self.__place_card(player, card)

            if not responded:
                await interaction.response.send_message(", ".join(map(str, player.hand)), ephemeral=True)

        await self.__post_interaction()

    @discord.ui.button(label='Place', style=discord.ButtonStyle.red)
    async def place(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not self.is_allowed(interaction):
            await interaction.response.defer()
            return

        player: Player = self.players[interaction.user.id]

        filtered_hand = self.__get_valid_hand(player)
        if len(filtered_hand) == 0:
            await interaction.response.send_message("No cards", ephemeral=True, delete_after=5)
            return

        view = CardChoice(filtered_hand)
        await interaction.response.send_message("_", view=view, ephemeral=True)
        await view.wait()
        card = view.get_selected()
        if card is None:
            if not self.__apply_stacked_cards(player, force=False):
                self.__add_notification('Timed out, taking card...', player)
                player.hand.extend(self.deck.take_cards(1))
            await self.__post_interaction()
            return

        await self.__place_card(player, card)
        await self.__post_interaction()

    @discord.ui.button(label='Show hand', style=discord.ButtonStyle.red)
    async def show(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self.players[interaction.user.id]
        await interaction.response.send_message(", ".join(map(str, player.hand)), ephemeral=True)

    @discord.ui.button(label='Show hand', style=discord.ButtonStyle.red)
    async def show(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = self.players[interaction.user.id]
        await interaction.response.send_message(", ".join(map(str, player.hand)), ephemeral=True)


@config.tree.command(name="maumau",
                     description="My first application Command",
                     guild=discord.Object(id=761624318291476482))
async def first_command(interaction):
    menu = JoinMenu()
    await interaction.response.send_message("_", view=menu)
    await menu.wait()

    menu = GameMenu([Player(x) for x in menu.user_ids])
    menu.followup = await interaction.followup.send(embed=menu.get_embed(), wait=True, view=menu)
    await menu.wait()
