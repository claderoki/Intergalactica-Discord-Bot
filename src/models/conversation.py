import datetime
import secrets

import discord
import peewee
from dateutil.relativedelta import relativedelta

from . import BaseModel
from .helpers import create


@create()
class Conversant(BaseModel):
    user_id = peewee.BigIntegerField(null=False)
    enabled = peewee.BooleanField(null=False, default=True)

    @classmethod
    def get_available(cls, exclusion_list=None):
        query = cls.select()
        query = query.where(cls.enabled == True)
        if exclusion_list:
            query = query.where(cls.user_id.not_in(exclusion_list))
        return query


@create()
class Participant(BaseModel):
    key = peewee.TextField(null=False, default=lambda: secrets.token_urlsafe(10))
    reveal = peewee.BooleanField(null=False, default=False)
    conversant = peewee.ForeignKeyField(Conversant, null=False)

    @property
    def user_id(self):
        return self.conversant.user_id

    async def send(self, *args, **kwargs):
        return await self.conversant.user.send(*args, **kwargs)


@create()
class Conversation(BaseModel):
    participant1 = peewee.ForeignKeyField(Participant, null=False)
    participant2 = peewee.ForeignKeyField(Participant, null=False)
    start_time = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())
    end_time = peewee.DateTimeField(null=True)
    finished = peewee.BooleanField(null=False, default=False)

    @property
    def duration(self):
        return relativedelta(datetime.datetime.utcnow(), self.start_time)

    @property
    def revealable(self):
        for participant in self.get_participants():
            if not participant.reveal:
                return False
        return True

    def get_other(self, current):
        if isinstance(current, int):
            return self.participant2.conversant.user_id if self.participant1.conversant.user_id == current else self.participant1.conversant.user_id
        elif isinstance(current, discord.User):
            return self.participant2.conversant.user if self.participant1.conversant.user_id == current.id else self.participant1.conversant.user
        elif isinstance(current, Participant):
            return self.participant2 if self.participant1 == current else self.participant1

    def get_user_ids(self):
        return (self.participant1.conversant.user_id, self.participant2.conversant.user_id)

    def get_participants(self):
        return (self.participant1, self.participant2)

    async def reveal(self):
        embed = discord.Embed()
        for participant in self.get_participants():
            other_user = self.get_other(participant).conversant.user
            embed.description = f"The person you have been speaking to is {other_user}, id: {other_user.id}"
            embed.set_author(name=str(other_user), icon_url=other_user.avatar_url)
            await participant.send(embed=embed)

    @classmethod
    def select_for(cls, conversant, finished=None):
        query = cls.select()
        c1 = Conversant.alias("c1")
        c2 = Conversant.alias("c2")
        query = query.join(c1, on=cls.participant1)
        query = query.switch(cls)
        query = query.join(c2, on=cls.participant2)
        query = query.where((cls.participant1 == conversant) | (cls.participant2 == conversant))
        if finished is not None:
            query = query.where(cls.finished == finished)
        return query
