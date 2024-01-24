import datetime
from enum import Enum

import discord
import emoji
import peewee

from .base import BaseModel, EnumField
from .helpers import create


@create()
class Ticket(BaseModel):
    class Type(Enum):
        support = 1
        concern = 2
        complaint = 3
        suggestion = 4

    class Status(Enum):
        open = 1
        closed = 2

    class CloseReason(Enum):
        denied = 1
        approved = 2
        resolved = 3

    text = peewee.TextField(null=False)
    user_id = peewee.BigIntegerField(null=False)
    guild_id = peewee.BigIntegerField(null=False)
    type = EnumField(Type, null=False)
    status = EnumField(Status, null=False, default=Status.open)
    close_reason = EnumField(CloseReason, null=True)
    anonymous = peewee.BooleanField(null=False, default=True)
    channel_id = peewee.BigIntegerField(null=True)
    message_id = peewee.BigIntegerField(null=True)
    created_at = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())

    @property
    def base_embed(self):
        guild = self.guild
        embed = discord.Embed(color=self.bot.get_dominant_color(guild))

        author_name = "anonymous" if self.anonymous else str(self.member)

        embed.set_author(name=f"{self.type.name.title()} by: {author_name}",
                         icon_url="https://cdn.discordapp.com/attachments/744172199770062899/765879281498587136/Blue_question_mark_icon.svg.png")
        embed.description = f"**{self.text}**\n\uFEFF"
        footer = []

        translate = self.bot.translate

        if self.status == self.Status.open:
            footer.append(translate("ticket_reply_instructions").format(id=str(self.id)))
        else:
            footer.append(translate("ticket_closed_info").format(reason=translate(self.close_reason.name)))

        if self.close_reason == self.CloseReason.approved:
            embed.color = discord.Color.green()
        elif self.close_reason == self.CloseReason.resolved:
            embed.color = discord.Color.green()
        elif self.close_reason == self.CloseReason.denied:
            embed.color = discord.Color.red()

        footer.append(translate("created_at"))
        embed.set_footer(text="\n".join(footer))
        embed.timestamp = self.created_at

        for reply in self.replies:
            icon_name = ":small_{color}_diamond:"
            color = "orange" if reply.type == Reply.Type.author else "blue"
            icon = emoji.emojize(icon_name.format(color=color))

            date_string = reply.replied_at.time().isoformat()

            embed.add_field(name=f"{icon} {translate(reply.type.name)} ({date_string})", value=f"{reply.text}\n\uFEFF",
                            inline=False)

        return embed

    @property
    def embed(self):
        embed = self.base_embed
        return embed

    @property
    def staff_embed(self):
        embed = self.base_embed
        return embed

    async def sync_message(self, channel=None):
        channel = self.channel

        if self.message_id is not None:
            try:
                message = await channel.fetch_message(self.message_id)
                await message.delete()
            except:
                pass

        message = await channel.send(embed=self.staff_embed)
        self.message_id = message.id
        self.channel_id = channel.id
        self.save()

        await self.member.send(embed=self.embed)


@create()
class Reply(BaseModel):
    class Type(Enum):
        author = 1
        staff = 2

    ticket = peewee.ForeignKeyField(Ticket, backref="replies", on_delete="CASCADE")
    text = peewee.TextField(null=False)
    type = EnumField(Type, null=False)
    anonymous = peewee.BooleanField(null=False, default=True)
    user_id = peewee.BigIntegerField(null=False)
    replied_at = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())
