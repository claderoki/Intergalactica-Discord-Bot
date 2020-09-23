import datetime
from enum import Enum

import peewee
import discord
import playhouse.pool
from emoji import emojize

import src.config as config
from src.discord.helpers.peewee import EmojiField
from .base import BaseModel

# db = playhouse.pool.PooledMySQLDatabase("polls_db", max_connections=32, stale_timeout=300, **config.mysql)

class Poll(BaseModel):
    anonymous = True

    question            = peewee.TextField       ()
    due_date            = peewee.DateTimeField   (default = lambda : datetime.datetime.now() + datetime.timedelta(days = 2))
    guild_id            = peewee.BigIntegerField ()
    author_id           = peewee.BigIntegerField ()
    type                = peewee.TextField       (default = "single")
    message_id          = peewee.BigIntegerField (null = True)
    channel_id          = peewee.BigIntegerField (null = True)
    result_channel_id   = peewee.BigIntegerField (null = True)
    ended               = peewee.BooleanField    (default = False)



    @property
    def due_date_passed(self) -> bool:
        current_date = datetime.datetime.now()
        return current_date >= self.due_date

    @property
    def author(self):
        return self.guild.get_member(self.author_id)

    @property
    def embed(self):
        embed = discord.Embed(title = self.question, color = self.bot.get_dominant_color(self.guild) )

        if self.type != "bool":
            embed.add_field(name = "\uFEFF", value = "\n".join([f"#{i+1}: {x.value}" for i, x in enumerate(self.options)]))

        footer = []

        footer.append(f"Due at: {self.due_date.replace(microsecond=0).isoformat(sep=' ')}")

        footer.append(f"type = {self.type}")

        embed.set_footer(text = "\n".join(footer))

        return embed


    async def send(self):
        msg = await self.channel.send(embed = self.embed)

        for option in self.options:
            await msg.add_reaction(option.reaction)

        return msg

    @property
    def result_embed(self):
        options = list(self.options)

        votes = sorted(
            {x.value:len(x.votes) for x in options}.items(),
            key = lambda k : k[1],
            reverse=True)

        embed = discord.Embed(
            title = f"Poll #{self.id} results",
            color = self.bot.get_dominant_color(self.guild)
            )

        lines = []

        total = sum([v for k,v in votes])
    
        for vote, count in votes:
            if total > 0:
                percentage = (count / total ) * 100
            else:
                percentage = 0

            lines.append(f"{vote}: {percentage}% ({count}) votes")

        embed.add_field(name = self.question, value = "\n".join(lines))
        return embed

    async def send_results(self):
        if self.result_channel_id is not None:
            channel = self.guild.get_channel(self.result_channel_id)
        else:
            channel = self.channel

        await channel.send(embed = self.result_embed)


class Option(BaseModel):
    poll     = peewee.ForeignKeyField (Poll, backref = "options")
    value    = peewee.TextField       ()
    reaction = EmojiField             ()

class Vote(BaseModel):
    user_id  = peewee.BigIntegerField ()
    option   = peewee.ForeignKeyField (Option, backref = "votes")


