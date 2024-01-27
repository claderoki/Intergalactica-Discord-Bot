from typing import List

import discord
import peewee

from src.models.base import rand
from src.models.pigeon import ExplorationAction, ExplorationActionScenario


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

        embed = discord.Embed()
        embed.title = f'{self.action.symbol} {self.action.name}'
        embed.description = f'{scenario.text}\n\n{winnings.format()}'
        await interaction.response.send_message(embed=embed)


class SpaceActionView(discord.ui.View):
    def __init__(self, actions: List[ExplorationAction]):
        super(self.__class__, self).__init__()
        self.actions = actions
        for action in self.actions:
            self.add_item(SpaceActionButton(action))
