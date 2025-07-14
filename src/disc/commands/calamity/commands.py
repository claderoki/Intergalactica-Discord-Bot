import datetime
import random
import typing

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.disc.commands.base.cog import BaseGroupCog
from src.models.calamity import CalamitySettings, Calamity, CalamityType


class CalamityCog(BaseGroupCog, name='calamity'):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.start_task(self.loop)
        print('CONSTR..')

    # @app_commands.command(name='shop', description='Open the calamity shop')
    # async def shop(self, interaction: discord.Interaction):
    #     await interaction.response.send_message(f'a')



    async def _create_calamity(self, settings: CalamitySettings):
        channel = self.bot.get_channel(settings.announcement_channel)
        if channel is None:
            print(f'channel {settings.announcement_channel} is none.')
            return

        calamity = Calamity.create(
            guild_id=settings.guild_id,
            estimated_arrival=datetime.datetime.utcnow(),
            actual_arrival=datetime.datetime.utcnow(),
            name='Helena',
            type=CalamityType.Hurricane,
        )
        await channel.send(f'Calamity {calamity.name} will arrive at {calamity.estimated_arrival}')

        settings.ready_for_calamity = False
        settings.save()

    @tasks.loop(seconds=60)
    async def loop(self):
        print('looping..')
        for settings in CalamitySettings.select().where(CalamitySettings.ready_for_calamity):
            await self._create_calamity(settings)


    @tasks.loop(seconds=60)
    async def loop2(self):
        print('looping..')
        for settings in CalamitySettings.select().where(CalamitySettings.ready_for_calamity):
            await self._create_calamity(settings)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CalamityCog(bot))
