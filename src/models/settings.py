from enum import Enum

import discord
import peewee

from .base import BaseModel, JsonField, EnumField
from src.discord.errors.base import SendableException
from src.models.human import Human

class Locale(BaseModel):
    name = peewee.CharField(primary_key = True, max_length = 5)

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(name = argument)

class Translation(BaseModel):
    message_key = peewee.BigIntegerField  (null = False)
    locale      = peewee.ForeignKeyField(Locale, column_name = "locale", default = "en_US")
    value       = peewee.BigIntegerField  (null = False)

class Settings(BaseModel):
    guild_id = peewee.BigIntegerField(null = False)
    locale   = peewee.ForeignKeyField(Locale, column_name = "locale", default = "en_US")

    def get_channel(self, name):
        for channel in self.channels:
            if channel.name == name:
                return channel.channel
        raise SendableException(f"{name} channel was not found. '{self.bot.command_prefix}channel set {name} #mention' to set.")

class NamedChannel(BaseModel):
    settings    = peewee.ForeignKeyField   (Settings, backref="channels")
    name        = peewee.TextField         (null = False)
    channel_id  = peewee.BigIntegerField   (null = False)

    @property
    def channel(self):
        return self.settings.guild.get_channel(self.channel_id)

class UserSetting(BaseModel):
    class Meta:
        indexes = (
            (("human", "code"), True),
        )

    human = peewee.ForeignKeyField (Human, null = False)
    code  = peewee.CharField       (null = False)
    value = peewee.TextField       (null = True)
