import peewee

from .base import BaseModel, TimeDeltaField

class InactiveChannelsSettings(BaseModel):
    guild_id     = peewee.BigIntegerField (null = False)
    enabled      = peewee.BooleanField    (null = False, default = True)
    timespan     = TimeDeltaField         (null = False)
    max_messages = peewee.IntegerField    (null = False, default = 4)
