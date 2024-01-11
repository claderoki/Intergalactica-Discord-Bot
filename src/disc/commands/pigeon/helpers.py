from typing import Optional

import emoji

from src.disc.cogs.pigeon.cog import get_active_pigeon
from src.models import Pigeon
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
        return cls('gold_modifier', amount, '❤🌻')


class Winnings:
    def __init__(self, *stats):
        self.stats = stats

    def format(self) -> str:
        return ' '.join([f'{x.emoji} {x.value}' for x in self.stats])


class PigeonHelper:
    # @config.cache.result
    def get_pigeon(self, user_id: int) -> Optional[Pigeon]:
        return get_active_pigeon(user_id)

    def get_all_locations(self):
        ExplorationPlanetLocation


    # public Map<Integer, FullExplorationLocation> getAllLocations() {
    #     Map<Integer, List<ExplorationAction>> actions = getAllActions();
    #     Map<Integer, FullExplorationLocation> locations = new HashMap<>();
    #     String query = """
    #         SELECT
    #             `exploration_planet_location`.`id` AS `id`,
    #             `planet_id`,
    #             IFNULL(`exploration_planet_location`.`image_url`, `exploration_planet`.`image_url`) AS `image_url`,
    #             `exploration_planet_location`.`name` AS `name`,
    #             `exploration_planet`.`name` AS `planet_name`
    #         FROM `exploration_planet_location`
    #         INNER JOIN `exploration_planet` ON `exploration_planet`.`id` = `exploration_planet_location`.`planet_id`
    #         WHERE `exploration_planet_location`.`active` = 1
    #     """;
    #     for(Result result: getMany(query)) {
    #         FullExplorationLocation location = new FullExplorationLocation(
    #             result.getInt("id"),
    #             result.getInt("planet_id"),
    #             result.getString("image_url"),
    #             result.getString("planet_name"),
    #             result.getString("name"),
    #             actions.get(result.getInt("id"))
    #         );
    #         locations.put(location.id(), location);
    #     }
    #     return locations;
    # }



class CheckResult:
    __slots__ = ('pigeon', 'errors')

    def __init__(self):
        self.pigeon = None
        self.errors = []
