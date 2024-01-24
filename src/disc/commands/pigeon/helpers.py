from typing import Optional, Iterable

import emoji

from src.config import config
from src.disc.cogs.pigeon.cog import get_active_pigeon
from src.models import Pigeon, Human
from src.models.pigeon import ExplorationPlanetLocation


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
        return cls('happiness', amount, '🌻')

    @classmethod
    def gold_modifier(cls, amount: float) -> 'PigeonStat':
        return cls('gold_modifier', amount, '❤')


class Winnings:
    def __init__(self, *stats):
        self.stats = stats

    def format(self) -> str:
        return ' '.join([f'{x.emoji} {x.value}' for x in self.stats])


class PigeonHelper:
    @config.cache(category='pigeon')
    def get_pigeon(self, user_id: int) -> Optional[Pigeon]:
        return get_active_pigeon(user_id)

    @config.cache(category='pigeon')
    def get_all_locations(self) -> Iterable[ExplorationPlanetLocation]:
        return ExplorationPlanetLocation

    def find_location(self, location_id: int) -> Optional[ExplorationPlanetLocation]:
        for location in self.get_all_locations():
            if location.id == location_id:
                return location


class HumanHelper:
    @config.cache(category='human')
    def get_human(self, user_id: int) -> Optional[int]:
        human, _ = Human.get_or_create(user_id=user_id)
        return human
