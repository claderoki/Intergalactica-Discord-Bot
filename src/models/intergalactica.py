import asyncio
import datetime
from enum import Enum

import discord
import peewee

from src.config import config
from src.disc.helpers.known_guilds import KnownGuild
from .base import BaseModel, EnumField, EmojiField
from .helpers import create
from .human import Human


@create()
class Reminder(BaseModel):
    channel_id = peewee.BigIntegerField(null=True)
    user_id = peewee.BigIntegerField(null=False)
    due_date = peewee.DateTimeField(null=False)
    message = peewee.TextField(null=False)
    sent = peewee.BooleanField(null=False, default=True)

    @classmethod
    def dm(cls, user_id: int, message: str, due_date: datetime.datetime):
        Reminder.create(
            user_id=user_id,
            channel_id=None,
            message=message,
            due_date=due_date
        )

class Earthling(BaseModel):
    user_id = peewee.BigIntegerField(null=False)
    guild_id = peewee.BigIntegerField(null=False)
    personal_role_id = peewee.BigIntegerField(null=True)
    human = peewee.ForeignKeyField(Human, column_name="global_human_id")
    last_active = peewee.DateTimeField(null=True)
    mandatory_role_warns = peewee.IntegerField(null=False, default=0)

    class Meta:
        indexes = (
            (('user_id', 'guild_id'), True),
        )

    @property
    def inactive(self):
        delta = datetime.timedelta(weeks=2)
        last_active: datetime.datetime = self.last_active or self.member.joined_at
        last_active = last_active.replace(tzinfo=datetime.timezone.utc)

        return (last_active + delta) < datetime.datetime.now(datetime.timezone.utc)

    @property
    def base_embed(self):
        member = self.member
        embed = discord.Embed(color=member.color or self.bot.get_dominant_color(self.guild))
        embed.set_author(name=self.member.display_name, icon_url=self.member.icon_url)
        return embed

    @property
    def personal_role(self):
        if self.guild is not None and self.personal_role_id is not None:
            return self.guild.get_role(self.personal_role_id)

    @personal_role.setter
    def personal_role(self, value):
        self.personal_role_id = value.id

    @classmethod
    def get_or_create_for_member(cls, member):
        return cls.get_or_create(
            guild_id=member.guild.id,
            user_id=member.id,
            human=config.bot.get_human(user=member)
        )


class Advertisement(BaseModel):
    guild_id = peewee.BigIntegerField(null=False)
    description = peewee.TextField(null=False)
    invite_url = peewee.TextField(null=True)
    log_channel_id = peewee.BigIntegerField(null=True)


class AdvertisementSubreddit(BaseModel):
    advertisement = peewee.ForeignKeyField(Advertisement, backref="subreddits")
    last_advertised = peewee.DateTimeField(null=True)
    name = peewee.TextField(null=False)
    hours_inbetween_posts = peewee.IntegerField(null=False, default=24)
    flair = peewee.TextField(null=True)
    active = peewee.BooleanField(null=False, default=True)

    @property
    def post_allowed(self):
        if self.last_advertised is None:
            return True

        allowed_at = self.last_advertised + datetime.timedelta(hours=self.hours_inbetween_posts)

        return allowed_at < datetime.datetime.utcnow()
