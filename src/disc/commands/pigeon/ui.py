import datetime
from typing import List

import discord

from src.disc.helpers.pretty import TimeDeltaHelper
from src.models.pigeon import ExplorationAction, ExplorationActionScenario, SpaceExploration, \
    SpaceExplorationScenarioWinnings, Pigeon
from src.utils.stats import Winnings


class SpaceActionButton(discord.ui.Button):
    def __init__(self, action: ExplorationAction):
        super().__init__(
            label=action.name,
            emoji=action.symbol
        )
        self.action = action


class SpaceActionView(discord.ui.View):
    def __init__(self, user: discord.User, actions: List[ExplorationAction], exploration: SpaceExploration):
        super(self.__class__, self).__init__()
        self.actions = actions
        self.user = user
        self.exploration = exploration
        self._used_action_ids = []
        self.winnings = self.__load_winnings()
        for action in self.actions:
            button = SpaceActionButton(action)
            button.disabled = action.id in self._used_action_ids
            button.callback = self.__create_callback_for(button)
            self.add_item(button)

    async def refresh(self):
        pass

    def __load_winnings(self) -> List[Winnings]:
        if self.exploration.actions_remaining == self.exploration.total_actions:
            return []
        else:
            winnings = []
            for winning in SpaceExplorationScenarioWinnings.for_exploration(self.exploration.id):
                self._used_action_ids.append(winning.action_id)
                winnings.append(winning.to_winnings())
            return winnings

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.exploration.actions_remaining <= 0:
            return False
        return interaction.user.id == self.user.id

    def __create_callback_for(self, button: SpaceActionButton):
        def wrapper(interaction: discord.Interaction):
            return self.action_callback(button, interaction)
        return wrapper

    async def __end(self, interaction: discord.Interaction):
        self.exploration.finished = True
        self.exploration.end_date = datetime.datetime.utcnow()
        winnings = Winnings.combine_all(*self.winnings)
        travel_format = TimeDeltaHelper.prettify(self.exploration.arrival_date - self.exploration.start_date)
        await interaction.followup.send(content=f'After {travel_format} of traveling, your pigeon gets home.\n' + winnings.format())
        self.stop()
        pigeon: Pigeon = self.exploration.pigeon
        pigeon.update_winnings(winnings)
        pigeon.status = Pigeon.Status.idle
        pigeon.save()
        self.exploration.save()

    async def action_callback(self, button: SpaceActionButton, interaction: discord.Interaction):
        scenario: ExplorationActionScenario = button.action.scenarios.rand().limit(1).first()
        winnings = scenario.to_winnings()

        # todo: category support.
        # if scenario.item_category is not None:
            # item_id = None
            # winnings.add_stat(HumanStat.item(item_id))
        embed = discord.Embed()
        embed.title = f'{button.action.symbol} {button.action.name}'
        embed.description = f'{scenario.text}\n\n{winnings.format()}'
        await interaction.response.send_message(embed=embed)

        SpaceExplorationScenarioWinnings.create(
            action=button.action,
            exploration=self.exploration,
            **winnings.to_dict()
        )
        self.winnings.append(winnings)

        self.exploration.actions_remaining -= 1
        if self.exploration.actions_remaining <= 0:
            await self.__end(interaction)
        else:
            self.exploration.save()
        button.disabled = True
        await self.refresh()
