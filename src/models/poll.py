import asyncio
import datetime
from enum import Enum

import discord
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
# import numpy as np
import peewee
from emoji import emojize

import src.discord.helpers.pretty as pretty
from src.discord.helpers.waiters import TimeDeltaWaiter
from src.utils.general import text_to_emojis
from .base import BaseModel, EnumField, EmojiField


def calculate_percentage(part, total):
    if total > 0:
        percentage = round((part / total) * 100, 2)
    else:
        percentage = 0

    if percentage % 1 == 0:
        return int(percentage)
    else:
        return percentage


class Poll(BaseModel):
    class Type(Enum):
        custom = 1
        bool = 2

    question = peewee.TextField(null=False)
    due_date = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=2))
    guild_id = peewee.BigIntegerField(null=False)
    author_id = peewee.BigIntegerField(null=False)
    message_id = peewee.BigIntegerField(null=True)
    channel_id = peewee.BigIntegerField(null=True)
    result_channel_id = peewee.BigIntegerField(null=True)
    created_at = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())
    ended = peewee.BooleanField(default=False)
    anonymous = peewee.BooleanField(null=False, default=False)
    max_votes_per_user = peewee.IntegerField(null=False, default=1)
    type = EnumField(Type, default=Type.custom)
    role_id_needed_to_vote = peewee.BigIntegerField(null=True)
    vote_percentage_to_pass = peewee.IntegerField(null=True)
    mention_role = peewee.BooleanField(null=False, default=False)
    pin = peewee.BooleanField(null=False, default=False)
    delete_after_results = peewee.BooleanField(null=False, default=False)

    @classmethod
    def from_template(cls, template):
        poll = cls(**template.shared_columns)
        if template.delta is not None:
            poll.due_date = datetime.datetime.utcnow() + TimeDeltaWaiter._convert(template.delta)
        return poll

    def create_bool_options(self):
        Option.create(value="yes", reaction=emojize(":white_heavy_check_mark:"), poll=self)
        Option.create(value="no", reaction=emojize(":prohibited:"), poll=self)

    def create_options(self, options):
        for i, option in enumerate(options):
            Option.create(value=option, reaction=emojize(f":keycap_{i + 1}:"), poll=self)

    @property
    def author(self):
        return self.guild.get_member(self.author_id)

    @property
    def embed(self):
        embed = discord.Embed(description=self.question, color=self.bot.get_dominant_color(self.guild))

        if self.type == self.Type.custom:
            values = []
            for i, option in enumerate(self.options):
                emoji = text_to_emojis(i + 1)[0]
                values.append(f"{emoji}: {option.value}")
            embed.description += "\n\n" + ("\n".join(values))
        embed.set_footer(text="Due date",
                         icon_url="https://cdn.discordapp.com/attachments/744172199770062899/761134294277029888/c.gif")
        embed.timestamp = self.due_date

        return embed

    @property
    def passed(self):
        if self.type == self.Type.bool:
            votes = self.votes
            percentage_needed = self.vote_percentage_to_pass or 51
            for vote in votes:
                if vote["text"] == "yes":
                    return vote["percentage"] >= percentage_needed

    async def send_results(self):
        channel = self.guild.get_channel(self.result_channel_id or self.channel_id)
        await channel.send(embed=await self.get_results_embed())

    async def send(self):
        content = f"<@&{self.role_id_needed_to_vote}>" if self.mention_role else None
        msg = await self.channel.send(content, embed=self.embed)
        for option in self.options:
            await msg.add_reaction(option.reaction)
        if self.pin:
            asyncio.gather(msg.pin())
        self.message_id = msg.id
        return msg

    @property
    def due_date_passed(self) -> bool:
        current_date = datetime.datetime.utcnow()
        return current_date >= self.due_date

    @property
    def votes(self):
        votes = {x: len(x.votes) for x in self.options}

        total = sum(votes.values())

        data = [{"percentage": calculate_percentage(count, total), "text": option.value, "count": count} for
                option, count in votes.items()]
        data.sort(key=lambda x: x["count"], reverse=True)
        return data

    async def get_results_embed(self):
        votes = [list(x.values()) for x in self.votes]
        votes.insert(0, ("%", "choice", "votes"))
        table = pretty.Table.from_list(votes, first_header=True)

        passed = self.passed

        embed = discord.Embed(description=f"Poll #{self.id} results\n\n**{self.question}?**\n{table.generate()}",
                              color=self.bot.get_dominant_color(self.guild))

        if self.type == self.Type.bool:
            if passed:
                embed.color = discord.Color.green()
                embed.set_footer(text="Vote passed!")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text="Vote did not pass.")

        return embed


class Option(BaseModel):
    poll = peewee.ForeignKeyField(Poll, backref="options", on_delete="CASCADE")
    value = peewee.TextField()
    reaction = EmojiField()


class Vote(BaseModel):
    user_id = peewee.BigIntegerField()
    option = peewee.ForeignKeyField(Option, backref="votes", on_delete="CASCADE")
    voted_on = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())

    class Meta:
        indexes = (
            (('user_id', 'option'), True),
        )


class PollTemplate(BaseModel):
    name = peewee.CharField(null=False, max_length=100)
    guild_id = peewee.BigIntegerField(null=False)

    channel_id = peewee.BigIntegerField(null=True)
    result_channel_id = peewee.BigIntegerField(null=True)
    anonymous = peewee.BooleanField(null=True)
    max_votes_per_user = peewee.IntegerField(null=True)
    type = EnumField(Poll.Type, null=True)
    role_id_needed_to_vote = peewee.BigIntegerField(null=True)
    delta = peewee.CharField(null=True)
    vote_percentage_to_pass = peewee.IntegerField(null=True)
    mention_role = peewee.BooleanField(null=True, default=False)
    pin = peewee.BooleanField(null=True, default=False)
    delete_after_results = peewee.BooleanField(null=True, default=False)

    class Meta:
        indexes = (
            (('name', 'guild_id'), True),
        )

    @property
    def shared_columns(self):
        return \
            {
                "guild_id": self.guild_id,
                "channel_id": self.channel_id,
                "result_channel_id": self.result_channel_id,
                "anonymous": self.anonymous,
                "max_votes_per_user": self.max_votes_per_user,
                "type": self.type,
                "role_id_needed_to_vote": self.role_id_needed_to_vote,
                "vote_percentage_to_pass": self.vote_percentage_to_pass,
                "pin": self.pin,
                "delete_after_results": self.delete_after_results,
                "mention_role": self.mention_role,
            }
