import asyncio
import datetime
from enum import Enum

import discord
import peewee

from .base import BaseModel, EmojiField, JsonField, EnumField
from .helpers import create


class SavedEmoji(BaseModel):
    name = peewee.CharField(null=False, unique=True)
    guild_id = peewee.BigIntegerField(null=False)
    emoji_id = peewee.BigIntegerField(null=False)

    def delete_instance(self, *args, **kwargs):
        emoji = self.bot.get_emoji(self.emoji_id)
        if emoji is not None:
            asyncio.gather(emoji.delete())
        super().delete_instance(*args, **kwargs)


class Giveaway(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    channel_id = peewee.BigIntegerField(null=False)
    user_id = peewee.BigIntegerField(null=False)
    message_id = peewee.BigIntegerField(null=False)
    due_date = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=1))
    role_id_needed = peewee.BigIntegerField(null=True)
    anonymous = peewee.BooleanField(null=False, default=False)
    finished = peewee.BooleanField(null=False, default=False)
    title = peewee.TextField(null=False)
    key = peewee.TextField(null=True)
    amount = peewee.IntegerField(null=False, default=1)

    @property
    def role_needed(self):
        return self.guild.get_role(self.role_id_needed)

    def get_embed(self):
        embed = discord.Embed(color=self.bot.get_dominant_color(self.guild))

        notes = []
        notes.append(f"**{self.title}**\n")
        if self.role_id_needed is not None:
            notes.append(f"`{self.role_needed.name}` role needed to participate")
        if self.amount > 1:
            notes.append(f"`{self.amount}` possible winners")

        embed.description = "\n".join(notes)

        footer = []
        footer.append("React with ✅ to join.")
        footer.append("Due at")

        embed.set_footer(text="\n".join(footer))
        embed.timestamp = self.due_date

        if not self.anonymous:
            embed.set_author(icon_url=self.user.avatar_url, name=f"Giveaway {self.id} by {self.user}")

        return embed


@create()
class DailyActivity(BaseModel):
    user_id = peewee.BigIntegerField(null=False)
    guild_id = peewee.BigIntegerField(null=False)
    message_count = peewee.IntegerField(null=False, default=0)
    date = peewee.DateField(null=False, default=lambda: datetime.date.today())

    class Meta:
        primary_key = False
        indexes = (
            (("user_id", "guild_id", "date"), True),
        )


@create()
class GameRole(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    role_id = peewee.BigIntegerField(null=False)
    game_name = peewee.CharField(null=False)

    class Meta:
        primary_key = False
        indexes = (
            (("role_id", "guild_id"), True),
        )


@create()
class GameRoleSettings(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    threshhold = peewee.IntegerField(null=False, default=2)
    log_channel_id = peewee.BigIntegerField(null=True)
    enabled = peewee.BooleanField(null=False, default=True)

    class Meta:
        indexes = (
            (("guild_id",), True),
        )
