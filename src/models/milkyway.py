from enum import Enum

import peewee

from .base import BaseModel, EnumField
from .helpers import create
from .human import Item


@create()
class MilkywaySettings(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    cost_per_day = peewee.IntegerField(null=False, default=500)
    active_limit = peewee.IntegerField(null=False, default=10)
    category_id = peewee.BigIntegerField(null=False)
    log_channel_id = peewee.BigIntegerField(null=False)
    godmode = peewee.BooleanField(null=False, default=False)


@create()
class Milkyway(BaseModel):
    class PurchaseType(Enum):
        item = 1
        points = 2
        none = 3

    class Status(Enum):
        pending = 1
        accepted = 2
        denied = 3
        expired = 4

    identifier = peewee.IntegerField(null=False)
    guild_id = peewee.BigIntegerField(null=False)
    user_id = peewee.BigIntegerField(null=False)
    channel_id = peewee.BigIntegerField(null=True)
    expires_at = peewee.DateTimeField(null=True)
    description = peewee.TextField(null=False)
    name = peewee.TextField(null=False)
    status = EnumField(Status, null=False, default=Status.pending)
    deny_reason = peewee.TextField(null=True)
    purchase_type = EnumField(PurchaseType, null=False)
    item = peewee.ForeignKeyField(Item, null=True)
    amount = peewee.IntegerField(null=True)
    days_pending = peewee.IntegerField(null=False)
    total_days = peewee.IntegerField(null=False, default=0)

    class Meta:
        indexes = (
            (("guild_id", "identifier"), True),
        )
