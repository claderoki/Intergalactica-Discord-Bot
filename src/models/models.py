import asyncio
import datetime

import peewee

from .base import BaseModel
import src.config as config

class Translation(BaseModel):
    message_key = peewee.BigIntegerField  (null = False)
    locale      = peewee.BigIntegerField  (default = "en_US")
    translation = peewee.BigIntegerField  (null = False)

