import asyncio
import random
import string
from typing import Optional, List, Dict

import discord

from src.config import config
from src.disc.commands import GameOverException
from src.disc.commands.horse_fight.game import Horse


class Map:
    def __init__(self):
        pass


class GameItself:
    def __init__(self):
        pass

    def generate_map(self) -> Map:
        pass


class GameMenu(discord.ui.View):
    def __init__(self):
        super(GameMenu, self).__init__()
        self.timeout = 2000
        self.log = []
        self.game_over = False
        self.followup = None

    async def on_timeout(self):
        print('Timed out...')

    def get_embed(self):
        embed = discord.Embed(description='Hmm')
        return embed

    async def _followup(self, **kwargs):
        await self.followup.edit(**kwargs)

    async def _end_game(self, winner: Horse):
        self.game_over = True
        await self._followup(content=f"Game ended, {winner} won",
                              embed=self.get_embed(),
                              view=self)
        self.stop()

    async def on_error(self, interaction, error: Exception, item) -> None:
        if not isinstance(error, GameOverException):
            await super().on_error(interaction, error, item)

    async def _update(self):
        await self._followup(embed=self.get_embed(), view=self)

    @discord.ui.button(label='Right', style=discord.ButtonStyle.red, emoji='🚪')
    async def right(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label='Left', style=discord.ButtonStyle.red, emoji='🚪')
    async def left(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label='Up', style=discord.ButtonStyle.red, emoji='🚪')
    async def up(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label='Down', style=discord.ButtonStyle.red, emoji='🚪')
    async def down(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()


@config.tree.command(name="horses",
                     description="Play Horses",
                     guild=discord.Object(id=761624318291476482))
async def horse(interaction: discord.Interaction):
    # menu = JoinMenu()
    await interaction.response.send_message("_")
    # await menu.wait()

    menu = GameMenu()
    menu.followup = await interaction.followup.send(embed=menu.get_embed(), wait=True, view=menu)
    try:
        await menu.start_bot_fight()
    except GameOverException:
        pass
