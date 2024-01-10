from distutils.cmd import Command
from typing import List, Optional, Union, Callable

import discord
from discord.app_commands import Group, ContextMenu
from discord.ext import commands
from discord import app_commands

from src.disc.commands.pigeon.helpers import PigeonHelper, Stat, CheckResult, Winnings, PigeonStat, HumanStat
import src.config as config
from src.models import Pigeon


def validation(settings: 'ValidationSettings'):
    def wrapper(func):
        def inner(f):
            f.extras['settings'] = settings
            return f

        if func is None:
            return inner
        else:
            return inner(func)
    return wrapper


class ValidationSettings:
    def __init__(self,
                 min_stats: List[Stat] = None,
                 required_status: Optional[Pigeon.Status] = None,
                 needs_active_pigeon: bool = True,
                 ):
        self.min_stats = min_stats
        self.required_status = required_status
        self.needs_active_pigeon = needs_active_pigeon


class Pigeon2(commands.GroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.helper = PigeonHelper()

    def __check(self,
                user_id: int,
                other: bool = False,
                settings: ValidationSettings = None,
                ) -> CheckResult:
        settings = settings or ValidationSettings()
        print(settings.required_status)
        result = CheckResult()
        result.pigeon = self.helper.get_pigeon(user_id)
        if settings.needs_active_pigeon and result.pigeon is None:
            result.errors.append('You don\'t have a pigeon.')

        if settings.required_status and result.pigeon.status != settings.required_status:
            result.errors.append(f'Your pigeon needs to be `{settings.required_status}` to perform this action.')

        if settings.min_stats is not None:
            pass

        return result

    async def __update_stat(self, interaction: discord.Interaction, stat: PigeonStat, cost: int, message: str):
        result = self.__check(user_id=interaction.user.id)
        if result.errors:
            await interaction.response.send_message(result.errors[0])
            return

        winnings = Winnings(stat, HumanStat.gold(-cost))
        result.pigeon.update_winnings(winnings)
        await interaction.response.send_message(message + '\n' + winnings.format())

    async def validate(self,
                       interaction: discord.Interaction,
                       user_id: int = None,
                       other: bool = False,
                       settings: ValidationSettings = None
                       ) -> Optional[Pigeon]:
        result = self.__check(user_id=user_id or interaction.user.id, other=other, settings=settings)
        if result.errors:
            await interaction.response.send_message(result.errors[0])
            raise Exception('Validation failed, can ignore')
        return result.pigeon

    @app_commands.command(name="feed", description="Feed your pigeon.")
    async def feed(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.food(20), 20, 'You feed that thing you call a pigeon.')

    @app_commands.command(name="clean", description="Clean your pigeon.")
    async def clean(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.cleanliness(20), 20, 'You clean that thing you call a pigeon.')

    @app_commands.command(name="play", description="Play with your pigeon.")
    async def play(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.happiness(20), 20,
                                 'You play with that thing you call a pigeon.')

    @app_commands.command(name="heal", description="Heal your pigeon.")
    async def heal(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.health(20), 20, 'You heal that thing you call a pigeon.')

    @validation(ValidationSettings(required_status=Pigeon.Status.idle))
    @app_commands.command(name="explore", description="Send your pigeon to space")
    async def explore(self, interaction: discord.Interaction) -> None:
        pigeon = await self.validate(interaction, **self.explore.extras)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pigeon2(bot))
