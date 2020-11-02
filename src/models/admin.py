import peewee

from .base import BaseModel

class SavedEmoji(BaseModel):
    name        = peewee.CharField        (null = False, unique = True)
    guild_id    = peewee.BigIntegerField  (null = False)
    emoji_id    = peewee.BigIntegerField  (null = False)
