from typing import Optional, Iterable

import emoji

from src.config import config
from src.disc.cogs.pigeon.cog import get_active_pigeon
from src.models import Pigeon, Human
from src.models.pigeon import ExplorationPlanetLocation


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
