from enum import Enum

import discord
from discord.ext import commands
import peewee

from src.models.base import BaseModel, EnumField
from src.models import Item
import src.config as config
from src.discord.cogs.core import BaseCog

# milkyway will be worth costs_per_day * 7, orion costs_per_day * 1
class MilkywaySettings(BaseModel):
    guild_id       = peewee.BigIntegerField (null = False)
    costs_per_day  = peewee.IntegerField    (null = False, default = 500)
    category_id    = peewee.BigIntegerField (null = False)
    log_channel_id = peewee.BigIntegerField (null = False) 

class Milkyway(BaseModel):
    class PurchaseType(Enum):
        item   = 1
        points = 2

    class Status(Enum):
        pending  = 1
        accepted = 2
        denied   = 3

    guild_id      = peewee.BigIntegerField (null = False)
    channel_id    = peewee.BigIntegerField (null = False)
    purchase_type = EnumField              (PurchaseType, null = False)
    status        = EnumField              (Status, null = False, default = Status.pending)
    deny_reason   = peewee.TextField       (null = True)
    item_id       = peewee.ForeignKeyField (Item, null = True)
    points_used   = peewee.IntegerField    (null = True)

class MilkywayHelper:
    __slots__ = ()

class MilkywayRepository:
    __slots__ = ()

    @classmethod
    def get_settings(cls, guild_id: int) -> MilkywaySettings:
        return None

class MilkywayCog(BaseCog, name = "Milkyway"):

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.group()
    async def milkyway(self, ctx):
        pass

    @milkyway.command(name = "setup")
    async def milkyway_setup(self, ctx):
        pass

def setup(bot):
    bot.add_cog(MilkywayCog(bot))