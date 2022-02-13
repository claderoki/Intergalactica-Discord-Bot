from enum import Enum

import peewee

from .base import BaseModel, EnumField
from .human import Item


# milkyway will be worth costs_per_day * 7, orion costs_per_day * 1
class MilkywaySettings(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    cost_per_day = peewee.IntegerField(null=False, default=500)
    category_id = peewee.BigIntegerField(null=False)
    log_channel_id = peewee.BigIntegerField(null=False)
    godmode = peewee.BooleanField(null=False, default=False)


class Milkyway(BaseModel):
    class PurchaseType(Enum):
        item = 1
        points = 2
        none = 3

    class Status(Enum):
        pending = 1
        accepted = 2
        denied = 3

    guild_id = peewee.BigIntegerField(null=False)
    channel_id = peewee.BigIntegerField(null=False)
    expires_at = peewee.DateTimeField(null=True)
    description = peewee.TextField(null=True)
    name = peewee.TextField(null=True)
    status = EnumField(Status, null=False, default=Status.pending)
    deny_reason = peewee.TextField(null=True)
    purchase_type = EnumField(PurchaseType, null=False)
    item_used = peewee.ForeignKeyField(Item, null=True)
    points_used = peewee.IntegerField(null=True)
