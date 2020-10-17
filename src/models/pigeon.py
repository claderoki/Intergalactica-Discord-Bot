import datetime

import peewee

from .base import BaseModel, EnumField
from .human import GlobalHuman

class Pigeon(BaseModel):
    name         = peewee.TextField       (null = False)
    global_human = peewee.ForeignKeyField (GlobalHuman, backref="pigeons")

class Fight(BaseModel):
    challenger = peewee.ForeignKeyField (GlobalHuman, null = False)
    challengee = peewee.ForeignKeyField (GlobalHuman, null = False)
    start_date = peewee.DateTimeField   (null = True)
    created_at = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())
    guild_id   = peewee.BigIntegerField (null = False)
    accepted   = peewee.BooleanField    (null = True) # null is pending, true is accepted, false is declined.
    won        = peewee.BooleanField    (null = True) # null is not ended yet, true means challenger won, false means challengee won
    ended      = peewee.BooleanField    (null = False, default = False)

    @property
    def start_date_passed(self) -> bool:
        return datetime.datetime.utcnow() >= self.start_date


class Bet(BaseModel):
    fight        = peewee.ForeignKeyField (Fight, backref = "bets")
    global_human = peewee.ForeignKeyField (GlobalHuman)
    amount       = peewee.BigIntegerField (null = False, default = 10)

    class Meta:
        indexes = (
            (('fight', 'global_human'), True),
        )
