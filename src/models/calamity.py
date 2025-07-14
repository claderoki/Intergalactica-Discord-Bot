import datetime
import enum
from typing import Optional

import peewee

from src.models.base import BaseModel, GuildIdField, EnumField, UserIdField, ChannelIdField
from src.models.helpers import create


class CalamityType(enum.Enum):
    Hurricane = 0


class Item:
    def __init__(self, id: int, name: str, description: Optional[str] = None, consumable: bool = False,
                 purchasable=True, cost: int = None):
        self.id = id
        self.name = name
        self.description = description
        self.consumable = consumable
        self.purchasable = purchasable
        self.cost = cost


class ItemType(enum.Enum):
    Bunker = Item(id=1, name='Bunker')
    Beans = Item(id=2, name='Beans', consumable=True, cost=50)
    Water = Item(id=3, name='Water', consumable=True, cost=50)


@create()
class Calamity(BaseModel):
    guild_id = GuildIdField(null=False)
    estimated_arrival = peewee.DateTimeField(null=False)
    actual_arrival = peewee.DateTimeField(null=True)
    name = peewee.TextField(null=False)
    type = EnumField(CalamityType, null=False)


@create()
class CalamitySettings(BaseModel):
    guild_id = GuildIdField(null=False)
    announcement_channel = ChannelIdField(null=False)
    ready_for_calamity = peewee.BooleanField(null=False, default=True)


@create()
class CalamityInventory(BaseModel):
    user_id = UserIdField(null=False)
    guild_id = GuildIdField(null=False)
    item_id = peewee.IntegerField(null=False)
    amount = peewee.IntegerField(null=False, default=1)
