import datetime

import peewee
import discord

from .base import BaseModel, EmojiField

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
        return f"https://www.google.com/maps/place/{self.latitude}+{self.longitude}/@{self.latitude},{self.longitude},20z"

class DailyReminder(BaseModel):
    time          = peewee.TimeField       (null = False)
    text          = EmojiField             (null = False)
    weekend       = peewee.BooleanField    (null = True)
    weekday       = peewee.BooleanField    (null = True)
    user_id       = peewee.BigIntegerField (null = False)
    last_reminded = peewee.DateField       (null = True)

class PersonalQuestion(BaseModel):
    value = peewee.TextField    (null = False)
    asked = peewee.BooleanField (null = False, default = False)

    @classmethod
    def get_random(cls):
        return cls.select().where(cls.asked == False).order_by(peewee.fn.Rand()).first()

    @property
    def embed(self):
        return discord.Embed(title = f"Question {self.id}", color = discord.Color.gold(),description = self.value)
