from typing import Optional

import emoji

from src.disc.cogs.pigeon.cog import get_active_pigeon
from src.models import Pigeon


class Stat:
    def __init__(self, name: str, value, emoji):
        self.name = name
        self.value = value
        self.emoji = emoji


class HumanStat(Stat):
    @classmethod
    def gold(cls, amount: int) -> 'HumanStat':
        return cls('gold', amount, emoji.emojize(":euro:"))


class PigeonStat(Stat):
    @classmethod
    def cleanliness(cls, amount: int) -> 'PigeonStat':
        return cls('cleanliness', amount, '💩')

    @classmethod
    def food(cls, amount: int) -> 'PigeonStat':
        return cls('food', amount, '🌾')

    @classmethod
    def experience(cls, amount: int) -> 'PigeonStat':
        return cls('experience', amount, '📊')

    @classmethod
    def health(cls, amount: int) -> 'PigeonStat':
        return cls('health', amount, '❤️')

    @classmethod
    def happiness(cls, amount: int) -> 'PigeonStat':
        return cls('happiness', amount, '❤🌻')


class Winnings:
    def __init__(self, *stats):
        self.stats = stats

    def format(self) -> str:
        return ' '.join([f'{x.emoji} {x.value}' for x in self.stats])


class PigeonHelper:
    # @config.cache.result
    def get_pigeon(self, user_id: int) -> Optional[Pigeon]:
        return get_active_pigeon(user_id)


class CheckResult:
    __slots__ = ('pigeon', 'errors')

    def __init__(self):
        self.pigeon = None
        self.errors = []
