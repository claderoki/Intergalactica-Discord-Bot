import asyncio
import random
import string
from typing import Optional, List, Dict

import discord

from src.config import config
from src.disc.commands import GameOverException
from src.disc.commands.horse_fight.game import Horse


class GameMenu(discord.ui.View):
    def __init__(self, min_horses: Optional[int] = 2):
        super(GameMenu, self).__init__()
        self.timeout = 2000
        self.all_ai = False
        self.wait_time = 0
        self.start_location = 0
        self.end_location = 100
        self.log = []
        self.game_over = False
        self.followup = None
        self.min_horses = min_horses
        horses = []
        self.__fill_with_ai(horses)
        self.horses: Dict[str, Horse] = {x.identifier: x for x in horses}
        self.__load()

    async def on_timeout(self):
        print('Timed out...')

    def __fill_with_ai(self, horses: List[Horse]):
        self.all_ai = len(horses) == 0
        for i in range(self.min_horses - len(horses)):
            horses.append(Horse(string.ascii_uppercase[i]))

    def __load(self):
        if self.all_ai:
            for child in self.children:
                self.remove_item(child)

    def get_embed(self):
        embed = discord.Embed()

        if len(self.log):
            value = []
            length = 0
            for i in range(len(self.log) - 1, -1, -1):
                notification = self.log[i]
                message = f'Round {notification.round} {notification.horse or ""}: {notification.message}'
                would_be_length = length + len(message) + 1
                if would_be_length >= (1024 / 2):
                    break
                length = would_be_length
                value.insert(0, message)
            embed.add_field(name='Log', value='\n'.join(value), inline=False)

        if self.game_over and len(self.stats) > 0:
            stats = []
            for stat in self.stats.values():
                stats.append(stat.readable())
            if len(stats) > 0:
                embed.add_field(name='Post game stats', value='\n'.join(stats), inline=False)

        h = []
        for horse in self.horses.values():
            h.append(f'🐎 {horse}: position {horse.location}/{self.end_location}')

        embed.add_field(name='Horses', value='\n'.join(h))

        if not self.game_over and self.wait_time > 0:
            embed.set_footer(text=f'\nWaiting {self.wait_time}s')
        return embed

    async def __followup(self, **kwargs):
        await self.followup.edit(**kwargs)

    async def __end_game(self, winner: Horse):
        self.game_over = True
        await self.__followup(content=f"Game ended, {winner} won",
                              embed=self.get_embed(),
                              view=self)
        self.stop()

    async def on_error(self, interaction, error: Exception, item) -> None:
        if not isinstance(error, GameOverException):
            await super().on_error(interaction, error, item)

    async def __update(self):
        embed = self.get_embed()
        await self.__followup(embed=embed, view=self)

    async def __cycle(self):
        for horse in self.horses.values():
            if horse.location == self.end_location:
                continue
            horse.location += random.randint(0, 2)
            if horse.location > self.end_location:
                horse.location = self.end_location

    async def start_bot_fight(self):
        while any(x for x in self.horses.values() if x.location != self.end_location):
            await self.__cycle()
            await asyncio.sleep(1)
            await self.__update()

    def __set_wait_time(self, time: int):
        if not self.all_ai:
            self.wait_time = time


@config.tree.command(name="horses",
                     description="Play Horses",
                     guild=discord.Object(id=761624318291476482))
async def horse(interaction: discord.Interaction):
    # menu = JoinMenu()
    await interaction.response.send_message("_")
    # await menu.wait()

    menu = GameMenu(4)
    menu.followup = await interaction.followup.send(embed=menu.get_embed(), wait=True, view=menu)
    try:
        await menu.start_bot_fight()
    except GameOverException:
        pass
