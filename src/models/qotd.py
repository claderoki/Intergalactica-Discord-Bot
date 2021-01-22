import datetime
from enum import Enum

import peewee

from .base import BaseModel, EnumField

class Category(BaseModel):
    name        = peewee.CharField (primary_key = True)
    description = peewee.TextField (null = False)

class Question(BaseModel):
    class Type(Enum):
        custom  = 0
        default = 1

    value    = peewee.TextField       (null = False)
    type     = EnumField              (Type, null = False, default = Type.default)
    guild_id = peewee.BigIntegerField (null = True)
    category = peewee.ForeignKeyField (Category, null = False, backref = "questions", column_name = "category", on_delete = "CASCADE")

class CategoryChannel(BaseModel):
    category     = peewee.ForeignKeyField (Category, null = True, backref = "category_channels", on_delete = "CASCADE")
    guild_id     = peewee.BigIntegerField (null = False)
    channel_id   = peewee.BigIntegerField (null = False)
    time_to_send = peewee.TimeField       (null = False, default = lambda : datetime.time(0,0,0))
    last_day     = peewee.DateField       (null = True)

class QuestionConfig(BaseModel):
    question         = peewee.ForeignKeyField (Question, backref = "question_configs", on_delete = "CASCADE")
    category_channel = peewee.ForeignKeyField (CategoryChannel, backref = "question_configs", on_delete = "CASCADE")
    asked            = peewee.BooleanField    (null = False, default = False)
