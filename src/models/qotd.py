import datetime
from enum import Enum

import peewee

from .base import BaseModel, EnumField

class Question(BaseModel):
    class Type(Enum):
        custom  = 0
        default = 1

    value    = peewee.TextField       (null = False)
    type     = EnumField              (Type, null = False, default = Type.default)
    guild_id = peewee.BigIntegerField (null = True)

class QuestionConfig(BaseModel):
    guild_id = peewee.BigIntegerField (null = False)
    question = peewee.ForeignKeyField (Question, backref = "question_configs")

class QuestionOfTheDayConfig(BaseModel):
    guild_id   = peewee.BigIntegerField (null = False)
    channel_id = peewee.BigIntegerField (null = False)
    timeout    = peewee.IntegerField    (null = False, default = 0)
    last_day   = peewee.DateField       (null = True)
