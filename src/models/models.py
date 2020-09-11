import asyncio
import datetime

import discord
import peewee
from playhouse.mysql_ext import JSONField

from .base import BaseModel
import src.config as config
from src.discord.helpers.peewee import JsonField

class Translation(BaseModel):
    message_key = peewee.BigIntegerField  (null = False)
    locale      = peewee.BigIntegerField  (default = "en_US")
    translation = peewee.BigIntegerField  (null = False)

class NamedEmbed(BaseModel):
    name = peewee.TextField(null = False)
    data = JsonField(null = False)

    @property
    def embed(self):
        return discord.Embed.from_dict(self.data)

    def select_fields(self, field_indexes):
        fields = []
        for index in field_indexes:
            fields.append(self.data["fields"][index])

        self.data["fields"] = fields

