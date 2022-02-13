import datetime

import peewee

from .base import BaseModel, TimeDeltaField


class GuildRewardsSettings(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    enabled = peewee.BooleanField(null=False, default=True)
    timeout = TimeDeltaField(null=False, default=datetime.timedelta(seconds=25))
    min_points_per_message = peewee.IntegerField(null=False, default=25)
    max_points_per_message = peewee.IntegerField(null=False, default=25)


class GuildRewardsProfile(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    user_id = peewee.BigIntegerField(null=False)
    points = peewee.BigIntegerField(null=False, default=0)

    class Meta:
        indexes = (
            (("guild_id", "user_id"), True),
        )
