import datetime
from enum import Enum

import peewee
import discord
import emoji

import src.config as config
from .base import BaseModel, EnumField

class Ticket(BaseModel):
    class Type(Enum):
        support = 1
        concern = 2
        complaint = 3
        suggestion = 4

    class Status(Enum):
        pending = 1
        approved = 2
        denied = 3

    text            = peewee.TextField       (null = False)
    user_id         = peewee.BigIntegerField (null = False)
    guild_id        = peewee.BigIntegerField (null = False)
    type            = EnumField              (Type, null = False)
    status          = EnumField              (Status, null = False, default = Status.pending )
    anonymous       = peewee.BooleanField    (null = False, default = True)
    channel_id      = peewee.BigIntegerField (null = True)
    message_id      = peewee.BigIntegerField (null = True)
    created_at      = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())

    @property
    def base_embed(self):
        guild = self.guild
        embed = discord.Embed(color = self.bot.get_dominant_color(guild) )

        author_name = "anonymous" if self.anonymous else str(self.member)

        embed.set_author(name = f"{self.type.name.title()} by: {author_name}", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Blue_question_mark_icon.svg/1024px-Blue_question_mark_icon.svg.png")
        embed.description = f"**{self.text}**\n\uFEFF"
        embed.set_footer(text = f"Use \"/reply {self.id} <response>\" to reply.\nCreated")
        embed.timestamp = self.created_at

        for reply in self.replies:
            icon_name = ":small_{color}_diamond:"
            color = "orange" if reply.type == Reply.Type.author else "blue"
            icon = emoji.emojize(icon_name.format(color = color))

            date_string = reply.replied_at.time().isoformat()

            embed.add_field(name = f"{icon} {reply.type.name.title()} at {date_string}", value = f"{reply.text}\n\uFEFF", inline = False)

        return embed



    @property
    def embed(self):
        embed = self.base_embed
        return embed

    @property
    def staff_embed(self):
        embed = self.base_embed
        # embed.set_footer(text = embed.footer.text)
        return embed


    async def sync_message(self, channel = None):
        channel = self.channel

        if self.message_id is not None:
            try:
                message = await channel.fetch_message(self.message_id)
                await message.delete()
            except:
                pass

        message = await channel.send(embed = self.staff_embed)
        self.message_id = message.id
        self.channel_id = channel.id
        self.save()

        await self.member.send(embed = self.embed)


class Reply(BaseModel):
    class Type(Enum):
        author = 1
        staff = 2

    ticket          = peewee.ForeignKeyField (Ticket, backref="replies", on_delete="CASCADE")
    text            = peewee.TextField       (null = False)
    type            = EnumField              (Type, null = False)
    anonymous       = peewee.BooleanField    (null = False, default = True)
    user_id         = peewee.BigIntegerField (null = False)
    replied_at      = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow() )