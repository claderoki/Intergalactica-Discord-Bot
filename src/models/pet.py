from typing import Tuple

import peewee

from src.models.base import BaseModel, GuildIdField, UserIdField
from src.models.helpers import create, drop
from src.utils.stats import Winnings


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


@create()
class PetCaretaker(BaseModel):
    user_id = UserIdField(null=False)
    pet = peewee.ForeignKeyField(Pet, null=False)
    points = peewee.IntegerField(null=False, default=0)
    trust = peewee.IntegerField(null=False, default=0)

    def update_winnings(self, winnings: Winnings):
        for stat in winnings:
            setattr(self, stat.name, stat.amount)

    class Meta:
        indexes = (
            (('user_id', 'pet_id'), True),
        )


@create()
class PetPerk(BaseModel):
    pet = peewee.ForeignKeyField(Pet, null=False)
    code = peewee.TextField(null=False)
    points = peewee.IntegerField(null=False, default=0)

    @property
    def perk(self) -> 'Perk':
        if self.code == Vampiric.code:
            return Vampiric()
        if self.code == MushroomExpert.code:
            return MushroomExpert()

    class Meta:
        indexes = (
            (('pet_id', 'code'), True),
        )


class Perk:
    code: str
    name: str
    cost: int
    emoji: str


class Vampiric(Perk):
    code = 'vampiric'
    name = 'Vampiric'
    cost = 120
    emoji = '🧛'


class MushroomExpert(Perk):
    code = 'mushroom_expert'
    name = 'Mushroom Expert'
    cost = 120
    emoji = '🍄'


"""
One channel with pet info?

Upgrades you can put points into (5/60)

SKILLS
- Treasure hunting
- Fighting
    - Damage
    - Health

PERKS
- Vampiric?
- Mushroom expert?

ABILITIES?
To fight with 
"""
