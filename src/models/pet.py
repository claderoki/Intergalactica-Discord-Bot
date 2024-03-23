from typing import Tuple

import peewee

from src.models.base import BaseModel, GuildIdField
from src.models.helpers import create


class Mob:
    __slots__ = ('name', 'health', 'damage')

    def __init__(self, name, health: int, damage: Tuple[int, int]):
        self.name = name
        self.health = health
        self.damage = damage


@create()
class Pet(BaseModel, Mob):
    guild_id = GuildIdField(null=False)
    alive = peewee.BooleanField(null=False, default=True)
    name = peewee.TextField(null=False)

    # stats
    health = peewee.BigIntegerField(null=False, default=100)

    # skills
    scavenging = peewee.BigIntegerField(null=False, default=0)
    fighting = peewee.BigIntegerField(null=False, default=0)

    @property
    def damage(self) -> Tuple[int, int]:
        return 6, 15

    class Meta:
        indexes = (
            (('guild_id', 'alive'), True),
        )


class PetPerk:
    pass


class Vampiric(PetPerk):
    code = 'vampiric'


class MushroomExpert(PetPerk):
    code = 'mushroom_expert'


"""
One channel with pet info?

Upgrades you can put points into (5/60)

SKILLS
- Treasure hunting
- Fighting
    - Damage
    - Health
    -

PERKS
- Vampiric?
- Mushroom expert?


ABILITIES?
To fight with 

"""
