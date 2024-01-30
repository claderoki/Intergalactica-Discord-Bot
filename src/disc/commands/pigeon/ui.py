from typing import List

import discord

from src.models.pigeon import ExplorationAction, ExplorationActionScenario, SpaceExploration, \
    SpaceExplorationScenarioWinnings
from src.utils.stats import HumanStat


class SpaceActionButton(discord.ui.Button):
    def __init__(self, action: ExplorationAction):
        super().__init__(
            label=action.name,
            emoji=action.symbol
        )
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        scenario: ExplorationActionScenario = self.action.scenarios.rand().limit(1).first()
        winnings = scenario.to_winnings()
        if scenario.item_category is not None:
            pass
            # item_id = None
            # winnings.add_stat(HumanStat.item(item_id))
            # todo: category support.
        embed = discord.Embed()
        embed.title = f'{self.action.symbol} {self.action.name}'
        embed.description = f'{scenario.text}\n\n{winnings.format()}'
        await interaction.response.send_message(embed=embed)
        self.disabled = True
        SpaceExplorationScenarioWinnings.create(
            action=self.action,
            exploration=self.view.exploration,
            **winnings.to_dict()
        )
        self.view.decrement_action()
        # await self.view.refresh()


class SpaceActionView(discord.ui.View):
    def __init__(self, user: discord.User, actions: List[ExplorationAction], exploration: SpaceExploration):
        super(self.__class__, self).__init__()
        self.actions = actions
        self.user = user
        for action in self.actions:
            self.add_item(SpaceActionButton(action))
        self.exploration = exploration

    def decrement_action(self):
        self.exploration.actions_remaining -= 1
        self.exploration.save()
        if self.exploration.actions_remaining <= 0:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.exploration.actions_remaining <= 0:
            return False
        return interaction.user.id == self.user.id
