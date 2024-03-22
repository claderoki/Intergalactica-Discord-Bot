import peewee

from src.models.base import BaseModel, GuildIdField
from src.models.helpers import create


@create()
class Pet(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    alive = peewee.BooleanField(null=False, default=True)
    name = peewee.TextField(null=False)

    scavenging = peewee.BigIntegerField(null=False, default=0)
    fighting = peewee.BigIntegerField(null=False, default=0)

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
"""
