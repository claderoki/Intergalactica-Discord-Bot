import datetime
from enum import Enum

import peewee
import discord

from .base import BaseModel, EnumField
from .human import Human
import src.config as config

class TemporaryChannel(BaseModel):
    class Status(Enum):
        pending  = 0
        accepted = 1
        denied   = 2

    guild_id            = peewee.BigIntegerField (null = False)
    name                = peewee.TextField       (null = False)
    topic               = peewee.TextField       (null = False)
    channel_id          = peewee.BigIntegerField (null = True)
    user_id             = peewee.BigIntegerField (null = False)
    expiry_date         = peewee.DateTimeField   (null = True)
    active              = peewee.BooleanField    (null = False, default = True)
    status              = EnumField              (Status, null = False, default = Status.pending)
    deny_reason         = peewee.TextField       (null = True)
    pending_milky_ways  = peewee.IntegerField    (null = True)

    @property
    def ticket_embed(self):
        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.set_author(icon_url = self.user.avatar_url, name = str(self.user))

        embed.description = f"A milkyway channel was requested.\nName: `{self.name}`\Topic: `{self.topic}`"

        footer = []
        footer.append(f"Use '/milkyway deny {self.id} <reason>' to deny this milkyway request")
        footer.append(f"Use '/milkyway accept {self.id}' to accept this milkyway request")
        embed.set_footer(text = "\n".join(footer))

        return embed

    async def update_channel_topic(self):
        await self.channel.edit(topic = f"{self.topic}\nexpires at {self.expiry_date} UTC")


    def set_expiry_date(self, delta):
        if self.expiry_date is None:
            self.expiry_date = datetime.datetime.utcnow()
        self.expiry_date = self.expiry_date + delta

    async def create_channel(self):
        for category in self.guild.categories:
            if category.id == 764486536783462442:
                break

        channel = await self.guild.create_text_channel(
            name = self.name,
            topic = self.topic,
            category = category
        )
        self.channel_id = channel.id
        return channel

class Earthling(BaseModel):
    user_id               = peewee.BigIntegerField  (null = False)
    guild_id              = peewee.BigIntegerField  (null = False)
    personal_role_id      = peewee.BigIntegerField  (null = True)
    human                 = peewee.ForeignKeyField  (Human, column_name = "global_human_id" )
    last_active           = peewee.DateTimeField    (null = True)

    class Meta:
        indexes = (
            (('user_id', 'guild_id'), True),
        )

    @property
    def inactive(self):
        last_active = self.last_active or self.member.joined_at
        return (last_active + config.inactive_delta) < datetime.datetime.utcnow()

    @property
    def rank_role(self):
        ranks = [
            748494880229163021,
            748494888844132442,
            748494890127851521,
            748494890169794621,
            748494891419697152,
            748494891751047183
        ]
        for role in self.member.roles:
            if role.id in ranks:
                return role

    @property
    def base_embed(self):
        member = self.member
        embed = discord.Embed(color = member.color or self.bot.get_dominant_color(self.guild) )
        embed.set_author(name = self.member.display_name, icon_url = self.member.icon_url)
        return embed

    @property
    def personal_role(self):
        return self.guild.get_role(self.personal_role_id)

    @personal_role.setter
    def personal_role(self, value):
        self.personal_role_id = value.id

    @classmethod
    def get_or_create_for_member(cls, member):
        return cls.get_or_create(
            guild_id = member.guild.id,
            user_id = member.id,
            human = Human.get_or_create(user_id = member.id)[0]
        )
