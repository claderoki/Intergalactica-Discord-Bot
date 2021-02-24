import datetime
import asyncio
import secrets

import peewee
import discord

from . import BaseModel

class Conversant(BaseModel):
    user_id = peewee.BigIntegerField (null = False)
    enabled = peewee.BooleanField    (null = False, default = True)

class Conversation(BaseModel):
    conversant1     = peewee.ForeignKeyField (Conversant, null = False)
    conversant1_key = peewee.TextField       (null = False, default = lambda : secrets.token_urlsafe(10))
    conversant2     = peewee.ForeignKeyField (Conversant, null = False)
    conversant2_key = peewee.TextField       (null = False, default = lambda : secrets.token_urlsafe(10))
    start_time      = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())
    end_time        = peewee.DateTimeField   (null = False)
    finished        = peewee.BooleanField    (null = False, default = False)

    @classmethod
    def select_for(cls, conversant, finished = None):
        query = cls.select()
        c1 = Conversant.alias("c1")
        c2 = Conversant.alias("c2")
        query = query.join(c1, on = cls.conversant1)
        query = query.switch(cls)
        query = query.join(c2, on = cls.conversant2)
        query = query.where((cls.conversant1 == conversant) | (cls.conversant2 == conversant))
        if finished is not None:
            query = query.where(cls.finished == finished)
        return query

