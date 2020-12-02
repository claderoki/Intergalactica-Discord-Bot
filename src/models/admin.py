import datetime

import peewee

from .base import BaseModel

class SavedEmoji(BaseModel):
    name        = peewee.CharField        (null = False, unique = True)
    guild_id    = peewee.BigIntegerField  (null = False)
    emoji_id    = peewee.BigIntegerField  (null = False)

class Location(BaseModel):
    latitude   = peewee.DecimalField  (null = False)
    longitude  = peewee.DecimalField  (null = False)
    created_on = peewee.DateTimeField (null = True, default = lambda : datetime.datetime.utcnow())
    name       = peewee.TextField     (null = False)

    @property
    def google_maps_url(self):
        return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
# 