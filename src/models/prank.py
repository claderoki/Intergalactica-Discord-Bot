from enum import Enum
import datetime

import emoji
import peewee

from .base import BaseModel, EnumField, EmojiField

class Prankster(BaseModel):
    class PrankType(Enum):
        nickname = 1
        role     = 2
        emoji    = 3

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

    @property
    def current_prank(self):
        if not self.pranked:
            return None

        classes = {
            self.PrankType.nickname : NicknamePrank,
            self.PrankType.emoji    : EmojiPrank,
            self.PrankType.role     : RolePrank,
        }
        cls = classes.get(self.prank_type)

        if cls is not None:
            query = cls.select()
            query = query.where(cls.victim == self)
            query = query.where(cls.finished == False)
            return query.first()

class Prank(BaseModel):
    duration  = datetime.timedelta(days = 1)
    cost      = None
    item_code = None

    class PurchaseType(Enum):
        gold = 1
        item = 2
        free = 3

    start_date    = peewee.DateTimeField    (null = False)
    end_date      = peewee.DateTimeField    (null = False)
    victim        = peewee.ForeignKeyField  (Prankster, null = False)
    pranked_by    = peewee.ForeignKeyField  (Prankster, null = False)
    finished      = peewee.BooleanField     (null = False, default = False)
    purchase_type = EnumField               (PurchaseType, null = False, default = PurchaseType.free)

    @property
    def should_apply_again(self):
        return False

    @property
    def end_date_passed(self):
        return datetime.datetime.utcnow() >= self.end_date

class NicknamePrank(Prank):
    duration  = datetime.timedelta(days = 1)
    prank_type = Prankster.PrankType.nickname
    cost       = 500
    item_code  = "jester_hat"

    new_nickname     = EmojiField (null = False)
    old_nickname     = EmojiField (null = False)

    @property
    def should_apply_again(self):
        return self.victim.member and self.victim.member.display_name != self.new_nickname

    async def apply(self):
        member = self.victim.member
        try:
            await member.edit(nick = self.new_nickname)
        except Exception as e:
            pass

    async def revert(self):
        member = self.victim.member
        await member.edit(nick = self.old_nickname)

class RolePrank(Prank):
    prank_type = Prankster.PrankType.role
    cost       = 10

    role_id = peewee.BigIntegerField(null = False)

    async def apply(self):
        pass
    async def revert(self):
        pass

class EmojiPrank(Prank):
    duration  = datetime.timedelta(minutes = 10)
    prank_type = Prankster.PrankType.emoji
    cost       = 150

    emoji = EmojiField(null = False, default = emoji.emojize(":pinching_hand:"))

    async def apply(self):
        pass
    async def revert(self):
        pass
