from typing import Any

import peewee

from .base import BaseModel, UserIdField
from .helpers import create


@create()
class GameStat(BaseModel):
    key = peewee.CharField(primary_key=True)
    user_id = UserIdField(null=False)
    value = peewee.TextField(null=False)

    @classmethod
    def increment_by(cls, key: str, user_id: int, value: Any):
        if isinstance(value, int):
            update = cls.value.cast('INTEGER') + 1
        else:
            update = cls.value + 1

        (cls
         .insert(key=key, user_id=user_id, value=value)
         .on_conflict(update={'value': update})
         .execute())

    class Meta:
        primary_key = False
        indexes = (
            (('key', 'user_id'), True),
        )
