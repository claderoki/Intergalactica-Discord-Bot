import datetime
from enum import Enum

import peewee
import discord
import playhouse.pool
from emoji import emojize

import src.config as config
from src.discord.helpers.peewee import ChannelField, UserField, GuildField, EmojiField
from .base import BaseModel

# db = playhouse.pool.PooledMySQLDatabase("polls_db", max_connections=32, stale_timeout=300, **config.mysql)

class Poll(BaseModel):
    anonymous = True

    question        = peewee.TextField       ()
    due_date        = peewee.DateTimeField   (default = lambda : datetime.datetime.now() + datetime.timedelta(days = 2))
    guild           = GuildField             ()
    author          = UserField              ()
    type            = peewee.TextField       (default = "single")
    message_id      = peewee.BigIntegerField (null = True)
    channel         = ChannelField           (null = True)
    ended           = peewee.BooleanField    (default = False)



    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(id = int(argument))


    @property
    def due_date_passed(self) -> bool:
        current_date = datetime.datetime.now()
        return current_date >= self.due_date


    @property
    def embed(self):
        embed = discord.Embed(title = self.question, color = discord.Color.purple() )

        if self.type != "bool":
            embed.add_field(name = "\uFEFF", value = "\n".join([f"#{i+1}: {x.value}" for i, x in enumerate(self.options)]))

        footer = []

        footer.append(f"Due at: {self.due_date.replace(microsecond=0).isoformat(sep=' ')}")

        embed.set_footer(text = "\n".join(footer))

        return embed


    async def send(self):
        msg = await self.channel.send(embed = self.embed)

        for option in self.options:
            await msg.add_reaction(option.reaction)

        return msg

    async def send_results(self):
        options = list(self.options)

        votes = sorted(
            {x.value:len(x.votes) for x in options}.items(),
            key = lambda k : k[1],
            reverse=True)

        embed = discord.Embed(
            title = f"Poll #{self.id} results",
            color = discord.Color.purple()
            )

        lines = []

        total = sum([v for k,v in votes])

        for vote, count in votes:
            percentage = (count / total ) * 100
            lines.append(f"{vote}: {percentage}% ({count}) votes")

        embed.add_field(name = self.question, value = "\n".join(lines))

        await self.channel.send(embed = embed)


class Option(BaseModel):
    poll     = peewee.ForeignKeyField (Poll, backref = "options")
    value    = peewee.TextField       ()
    reaction = EmojiField             ()

class Vote(BaseModel):
    user     = UserField              ()
    option   = peewee.ForeignKeyField (Option, backref = "votes")


