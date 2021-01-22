
import discord
import peewee

from .base import BaseModel, JsonField, EnumField
from src.discord.errors.base import SendableException

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

class NamedEmbed(BaseModel):
    settings    = peewee.ForeignKeyField   (Settings, backref="embeds")
    name        = peewee.TextField         (null = False)
    data        = JsonField                (null = False)

    def _set_color_if_default(self):
        if "color" not in data:
            data["color"] = self.bot.get_dominant_color(self.settings.guild)

    @property
    def embed(self):
        embed = discord.Embed.from_dict(self.data)

        if embed.color == discord.Embed.Empty:
            embed.color = self.bot.get_dominant_color(self.settings.guild)

        return embed

    def get_embed_only_selected_fields(self, field_indexes):
        embed = self.embed

        fields = []
        for index in field_indexes:
            fields.append(self.data["fields"][index])

        self.data["fields"] = fields

        return self.embed

class NamedChannel(BaseModel):
    settings    = peewee.ForeignKeyField   (Settings, backref="channels")
    name        = peewee.TextField         (null = False)
    channel_id  = peewee.BigIntegerField   (null = False)

    @property
    def channel(self):
        return self.settings.guild.get_channel(self.channel_id)