import datetime
import asyncio

import peewee
import discord

from . import BaseModel

class Conversant(BaseModel):
    pass

class Conversation(BaseModel):
    conversant1 = peewee.ForeignKeyField(Conversant, null = False)
    conversant2 = peewee.ForeignKeyField(Conversant, null = False)
    start_time  = None
    end_time    = None
    finished    = None
