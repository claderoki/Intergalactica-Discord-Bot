import datetime

import peewee
import discord

from .base import BaseModel
from .human import Human
import src.config as config

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
        table_name = "human"

    @property
    def inactive(self):
        date_implemented = datetime.datetime(2020,9,21, 0,0,0,0)
        # member = self.member
        # last_active = self.last_active or member.joined_at
        last_active = self.last_active or date_implemented
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
