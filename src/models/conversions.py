import math
from enum import Enum

import peewee

from .base import BaseModel, EnumField, GuildIdField
from .helpers import create
from ..classes import Labeled


class StoredUnit(BaseModel, Labeled):
    rate = peewee.DoubleField(null=False)
    name = peewee.TextField(null=False)
    is_base = peewee.BooleanField(null=False, default=False)
    code = peewee.TextField(null=False)
    symbol = peewee.TextField(null=False)

    def to(self, to, value: float, squared: bool = False) -> float:
        if self.code == "c" and to.code == "f":
            return (value * 1.8) + 32
        elif self.code == "f" and to.code == "c":
            return (value - 32) / 1.8
        elif squared:
            return ((to.rate * (math.sqrt(value))) / self.rate) ** 2
        else:
            return (to.rate * value) / self.rate

    def get_key(self):
        return self.id

    def get_label(self):
        return self.name

    @property
    def should_exclude_symbol(self):
        if "$" in self.symbol and self.symbol != '$':
            return True
        if "£" in self.symbol and self.symbol != '£':
            return True
        if "." in self.symbol:
            return True
        if self.symbol.lower() in ("p", "k", "s", "r", "t", "e", "d", "m", "km", "g", "ar", "l", "le", "ush", "br"):
            return True
        return False


@create()
class Currency(StoredUnit):
    pass


class MeasurementSubType(Enum):
    length = 1
    temperature = 2
    mass = 3


@create()
class Measurement(StoredUnit):
    subtype = EnumField(MeasurementSubType, null=False)
    squareable = peewee.BooleanField(null=False, default=False)


@create()
class EnabledCurrencySymbols(BaseModel):
    symbol = peewee.TextField(null=False)
    currency = peewee.ForeignKeyField(Currency, null=False)
    guild_id = GuildIdField(null=False)
