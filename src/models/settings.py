import peewee

from src.models.human import Human
from .base import BaseModel
from .helpers import create


@create()
class Locale(BaseModel):
    name = peewee.CharField(primary_key=True, max_length=5)

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(name=argument)


@create()
class Translation(BaseModel):
    message_key = peewee.BigIntegerField(null=False)
    locale = peewee.ForeignKeyField(Locale, column_name="locale", default="en_US")
    value = peewee.BigIntegerField(null=False)


@create()
class UserSetting(BaseModel):
    class Meta:
        indexes = (
            (("human", "code"), True),
        )

    human = peewee.ForeignKeyField(Human, null=False)
    code = peewee.CharField(null=False)
    value = peewee.TextField(null=True)
