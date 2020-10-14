import datetime
import discord
from enum import Enum
import io

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import peewee
from emoji import emojize

import src.config as config
from .base import BaseModel, EnumField, EmojiField
from src.discord.helpers.waiters import TimeDeltaWaiter


def calculate_percentage(part, total):
    if total > 0:
        percentage = round( (part / total ) * 100, 2)
    else:
        percentage = 0

    if percentage % 1 == 0:
        return int(percentage)
    else:
        return percentage


class Poll(BaseModel):
    class Type(Enum):
        custom = 1
        bool   = 2

    question                = peewee.TextField       (null = False)
    due_date                = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow() + datetime.timedelta(days = 2))
    guild_id                = peewee.BigIntegerField (null = False)
    author_id               = peewee.BigIntegerField (null = False)
    message_id              = peewee.BigIntegerField (null = True)
    channel_id              = peewee.BigIntegerField (null = True)
    result_channel_id       = peewee.BigIntegerField (null = True)
    created_at              = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())
    ended                   = peewee.BooleanField    (default = False)
    anonymous               = peewee.BooleanField    (null = False, default = False)
    max_votes_per_user      = peewee.BooleanField    (null = False, default = 1)
    type                    = EnumField              (Type, default = Type.custom)
    role_id_needed_to_vote  = peewee.BigIntegerField (null = True)
    vote_percentage_to_pass = peewee.IntegerField    (null = True)


    @classmethod
    def from_template(cls, template):
        poll = cls(**template.shared_columns)
        if template.delta is not None:
            poll.due_date = datetime.datetime.utcnow() + TimeDeltaWaiter._convert(template.delta)
        return poll


    def create_bool_options(self):
        Option.create(value = "yes", reaction = emojize(":white_heavy_check_mark:"), poll = self)
        Option.create(value = "no",  reaction = emojize(":prohibited:"),             poll = self)

    def create_options(self, options):
        for i, option in enumerate(options):
            Option.create(value = option, reaction = emojize(f":keycap_{i+1}:"), poll = self)

    @property
    def author(self):
        return self.guild.get_member(self.author_id)

    @property
    def embed(self):
        embed = discord.Embed(description = self.question, color = self.bot.get_dominant_color(self.guild) )

        if self.type == self.Type.custom:
            values = []
            for i, option in enumerate(self.options):
                emoji = self.bot.text_to_emojis(i+1)[0]
                values.append(f"{emoji}: {option.value}")
            embed.description +=  "\n\n" + ( "\n".join(values) )
        embed.set_footer(text = "Due date", icon_url = "https://cdn.discordapp.com/attachments/744172199770062899/761134294277029888/c.gif")
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
        await channel.send(embed = await self.get_results_embed() )

    async def send(self):
        msg = await self.channel.send(embed = self.embed)
        for option in self.options:
            await msg.add_reaction(option.reaction)
        return msg

    def generate_question(self, mention = False):
        changes = list(self.changes)

        lines = []
        lines.append("Would you like to ")

        for change in changes:
            lines.append(change.to_string(mention = mention))

        sep = " " if len(changes) == 1 else "\n"
        return sep.join(lines) + "?"

    @property
    def due_date_passed(self) -> bool:
        current_date = datetime.datetime.utcnow()
        return current_date >= self.due_date

    @property
    def votes(self):
        votes = {x:len(x.votes) for x in self.options}

        total = sum(votes.values())

        data = [ {"percentage": calculate_percentage(count, total), "text": option.value, "count": count} for option, count in votes.items() ]
        data.sort(key = lambda x : x["count"], reverse = True)
        return data

    def get_result_image_url(self):
        votes = self.votes

        plt.rcdefaults()
        plt.style.use('seaborn-pastel')
        plt.rcParams.update({'figure.autolayout': True})
        fig, ax = plt.subplots()
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(ticker.MaxNLocator(integer=True))

        bar_x = list(range(len(votes)))
        bar_height = [x["count"] for x in votes]
        bar_tick_label = [x["text"] for x in votes]
        bar_label = [str(x["percentage"]) + "%" for x in votes]

        bar_plot = plt.bar(bar_x, bar_height, tick_label=bar_tick_label)

        for idx,rect in enumerate(bar_plot):
            height = rect.get_height()
            x = rect.get_x() + rect.get_width()/2.
            y = 0.5*height
            ax.text(x, y, bar_label[idx], ha='center', va='bottom', rotation=0)

        plt.ylim(0,20)

        if len(self.changes) > 0:
            ax.set_title(self.generate_question(mention = False))
        else:
            ax.set_title(self.question)

        ax.margins(0.3)
        ax.axis('tight')
        fig.tight_layout()

        stream = io.BytesIO()
        plt.savefig(stream, format = 'png', transparent = False)
        stream.seek(0)
        return self.bot.store_file(stream, "results.png")

    async def get_results_embed(self):
        url = await self.get_result_image_url()

        changes = list(self.changes)
        passed = self.passed

        embed = discord.Embed(description = f"Poll #{self.id} results", color = self.bot.get_dominant_color(self.guild))

        if self.type == self.Type.bool:
            if passed:
                #TODO: translate!
                embed.color = discord.Color.green()
                embed.set_footer(text = "Vote passed!")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text = "Vote did not pass.")

            if len(changes) > 0 and passed:
                embed.set_footer(text = "Changes have been implemented.")

        embed.set_image(url = url)

        return embed

class Change(BaseModel):
    class Type(Enum):
        textchannel  = 1
        voicechannel = 2
        role         = 3

    class Action(Enum):
        create = 1
        delete = 2
        edit   = 3


    action      = peewee.TextField       (null = False)
    implemented = peewee.BooleanField    (null = False, default = False)
    type        = EnumField              (Type, null = False)
    poll        = peewee.ForeignKeyField (Poll, null = False, backref = "changes", on_delete = "CASCADE")

    def create_param(self, key, value):
        return Parameter.create(change = self, key = key, value = value)

    async def _delete_action(self):
        subject = self.subject
        await subject.delete()

    async def _create_action(self):
        parameters = self.parameters

        if self.type == self.Type.textchannel:
            return await self.poll.guild.create_text_channel(**parameters)

    def to_string(self, mention):
        action = self.action

        if action == "delete":
            return f"{action} {self.subject if not mention else self.subject.mention}"
        elif action == "create":
            parameters = self.parameters
            return f"{action} {self.type.name} " + (", ".join([x +"="+ parameters[x] for x in parameters]))

    async def implement(self):
        if self.action == "delete":
            return await self._delete_action()
        elif self.action == "create":
            return await self._create_action()

    async def revert(self):
        pass

    @property
    def parameters(self):
        return {parameter.key:parameter.value for parameter in self.parameters_select}

    @property
    def subject(self):
        if self.action == "create":
            return None

        parameters = self.parameters

        if self.type == self.Type.textchannel:
            return self.poll.guild.get_channel(int(parameters["id"]))

class Parameter(BaseModel):
    key    = peewee.TextField(null = False)
    value  = peewee.TextField(null = False)
    change = peewee.ForeignKeyField(Change, backref = "parameters_select", null = False, on_delete = "CASCADE")

class Option(BaseModel):
    poll     = peewee.ForeignKeyField (Poll, backref = "options", on_delete = "CASCADE")
    value    = peewee.TextField       ()
    reaction = EmojiField             ()

class Vote(BaseModel):
    user_id  = peewee.BigIntegerField ()
    option   = peewee.ForeignKeyField (Option, backref = "votes", on_delete = "CASCADE")
    voted_on = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())

    class Meta:
        indexes = (
            (('user_id', 'option'), True),
        )

class PollTemplate(BaseModel):
    name                    = peewee.CharField       (null = False, max_length = 100)
    guild_id                = peewee.BigIntegerField (null = False)

    channel_id              = peewee.BigIntegerField (null = True)
    result_channel_id       = peewee.BigIntegerField (null = True)
    anonymous               = peewee.BooleanField    (null = True)
    max_votes_per_user      = peewee.BooleanField    (null = True)
    type                    = EnumField              (Poll.Type, null = True)
    role_id_needed_to_vote  = peewee.BigIntegerField (null = True)
    delta                   = peewee.CharField       (null = True)
    vote_percentage_to_pass = peewee.IntegerField    (null = True)


    class Meta:
        indexes = (
            (('name', 'guild_id'), True),
        )


    @property
    def shared_columns(self):
        return \
        {
            "guild_id"                : self.guild_id,
            "channel_id"              : self.channel_id,
            "result_channel_id"       : self.result_channel_id,
            "anonymous"               : self.anonymous,
            "max_votes_per_user"      : self.max_votes_per_user,
            "type"                    : self.type,
            "role_id_needed_to_vote"  : self.role_id_needed_to_vote,
            "vote_percentage_to_pass" : self.vote_percentage_to_pass
        }
