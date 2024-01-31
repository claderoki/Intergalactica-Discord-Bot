import datetime
from typing import List

import discord

from src.models.pigeon import ExplorationAction, ExplorationActionScenario, SpaceExploration, \
    SpaceExplorationScenarioWinnings


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
        self.winnings = []
        for action in self.actions:
            button = SpaceActionButton(action)
            button.callback = self.__create_callback_for(button)
            self.add_item(button)
        self.exploration = exploration

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.exploration.actions_remaining <= 0:
            return False
        return interaction.user.id == self.user.id

    def __create_callback_for(self, button: SpaceActionButton):
        def wrapper(interaction: discord.Interaction):
            return self.action_callback(button, interaction)
        return wrapper

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

        button.disabled = True
        self.winnings.append(SpaceExplorationScenarioWinnings.create(
            action=button.action,
            exploration=self.exploration,
            **winnings.to_dict()
        ))

        self.exploration.actions_remaining -= 1
        if self.exploration.actions_remaining <= 0:
            self.exploration.finished = True
            self.exploration.end_date = datetime.datetime.utcnow()
            self.winnings
            await interaction.followup.send(content='After {x} of traveling, your pigeon returns home.')
            self.stop()
        self.exploration.save()

