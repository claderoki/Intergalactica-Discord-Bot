import datetime

import peewee
import discord

from .base import BaseModel
from .human import Human
import src.config as config

class TemporaryChannel(BaseModel):
    guild_id    = peewee.BigIntegerField (null = False)
    name        = peewee.TextField       (null = False)
    description = peewee.TextField       (null = False)
    channel_id  = peewee.BigIntegerField (null = True)
    user_id     = peewee.BigIntegerField (null = False)
    expiry_date = peewee.DateTimeField   (null = True)
    active      = peewee.BooleanField    (null = False, default = True)

    # @property
    # def expired(self):
    #     return datetime.datetime.utcnow() >= self.expiry_date

    async def create_channel(self):
        for category in self.guild.categories:
            if category.id == 742243893743190116:
                break

        channel = await self.guild.create_text_channel(
            name = self.name,
            description = self.description,
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
