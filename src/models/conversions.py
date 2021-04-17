from enum import Enum

import peewee

from .base import BaseModel, EnumField

class StoredUnit(BaseModel):
    rate    = peewee.DoubleField(null = False)
    name    = peewee.TextField(null = False)
    is_base = peewee.BooleanField(null = False, default = False)
    code    = peewee.TextField(null = False)
    symbol  = peewee.TextField(null = False)

class Currency(StoredUnit):
    pass

class MeasurementSubType(Enum):
    length      = 1
    temperature = 2

class Measurement(StoredUnit):
    subtype = EnumField(MeasurementSubType, null = False)

