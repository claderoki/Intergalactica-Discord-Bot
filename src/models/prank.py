from enum import Enum
import datetime

import peewee

from .base import BaseModel, EnumField, EmojiField

class Prankster(BaseModel):
    class PrankType(Enum):
        nickname = 1

    user_id      = peewee.BigIntegerField  (null = False)
    guild_id     = peewee.BigIntegerField  (null = False)
    last_pranked = peewee.DateTimeField    (null = True)
    enabled      = peewee.BooleanField     (null = False, default = False)
    pranked      = peewee.BooleanField     (null = False, default = False)
    prank_type   = EnumField               (PrankType, null = True)

    @property
    def days_ago_last_pranked(self):
        if self.last_pranked is not None:
            return (datetime.datetime.utcnow() - self.last_pranked).days

class Prank(BaseModel):
    end_date     = peewee.DateTimeField    (null = False)
    start_date   = peewee.DateTimeField    (null = False)
    victim       = peewee.ForeignKeyField  (Prankster, null = False)
    pranked_by   = peewee.ForeignKeyField  (Prankster, null = False)
    finished     = peewee.BooleanField     (null = False, default = False)

    @property
    def end_date_passed(self):
        return datetime.datetime.utcnow() >= self.end_date

class NicknamePrank(Prank):
    new_nickname     = EmojiField (null = False)
    old_nickname     = EmojiField (null = False)

    async def apply(self):
        member = self.victim.member
        await member.edit(nick = self.new_nickname)

    async def revert(self):
        member = self.victim.member
        await member.edit(nick = self.old_nickname)
