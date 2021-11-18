from enum import Enum

import peewee

from .base import BaseModel, EnumField

class SecretSanta(BaseModel):
    guild_id   = peewee.BigIntegerField (null = False)
    start_date = peewee.DateTimeField   (null = False)
    active     = peewee.BooleanField    (null = False, default = False)
    started_at = peewee.DateTimeField   (null = True)

class SecretSantaParticipant(BaseModel):
    class Type(Enum):
        monetary     = "Monetary"
        non_monetary = "Non monetary"

    user_id      = peewee.BigIntegerField    (null = False)
    type         = EnumField                 (Type, null = False)
    description  = peewee.TextField          (null = False)
    secret_santa = peewee.ForeignKeyField    (SecretSanta, null = False, backref = "participants")
    giftee       = peewee.DeferredForeignKey ("SecretSantaParticipant", null = True)
