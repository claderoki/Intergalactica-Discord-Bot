from typing import List, Optional

import discord
from discord.ext import commands
from discord import app_commands

from src.models import Pigeon
import src.config as config


class Stat:
    def __init__(self, name: str, amount):
        self.name = name
        self.amount = amount


class HumanStat(Stat):
    @classmethod
    def gold(cls, amount: int) -> 'HumanStat':
        return cls('gold', amount)


class PigeonStat(Stat):
    @classmethod
    def cleanliness(cls, amount: int) -> 'PigeonStat':
        return cls('cleanliness', amount)

    @classmethod
    def food(cls, amount: int) -> 'PigeonStat':
        return cls('food', amount)


class Winnings:
    def __init__(self, *stats):
        self.stats = stats


class PigeonHelper:
    @config.cache.result
    def get_pigeon(self, human_id: int) -> Optional[Pigeon]:
        return Pigeon.get_or_none(human=human_id, condition=Pigeon.Condition.active)

    @config.cache.result
    def get_pigeon_from_user_id(self, user_id: int) -> Pigeon:
        pass


class Pigeon2(commands.GroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="feed", description="Feed your pigeon.")
    async def feed(self, interaction: discord.Interaction) -> None:
        winnings = Winnings(PigeonStat.food(20), HumanStat.gold(-20))
        await interaction.response.send_message("Hello from sub command 1")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pigeon2(bot))
