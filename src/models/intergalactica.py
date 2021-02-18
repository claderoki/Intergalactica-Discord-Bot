import datetime
from enum import Enum
import asyncio
import random

import peewee
import discord

from .base import BaseModel, EnumField, EmojiField
from .human import Human
import src.config as config

class MentionGroup(BaseModel):
    name     = peewee.CharField       (null = False)
    guild_id = peewee.BigIntegerField (null = False)

    def join(self, user, is_owner = True):
        return MentionMember.get_or_create(
            user_id  = user.id,
            group    = self,
            is_owner = is_owner
        )[1]

    def leave(self, user):
        query = MentionMember.delete()
        query = query.where(MentionMember.user_id == user.id)
        query = query.where(MentionMember.group == self)
        return query.execute()

    def is_member(self, user):
        try:
            MentionMember.get(user_id = user.id, group = self)
        except MentionMember.DoesNotExist:
            return False
        else:
            return True

    @property
    def mention_string(self):
        mentions = []
        for mention_member in self.mention_members:
            mentions.append(mention_member.mention)
        return ", ".join(mentions)

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(name = argument, guild_id = ctx.guild.id)

    class Meta:
        indexes = (
            (("guild_id", "name"), True),
        )


class MentionMember(BaseModel):
    user_id  = peewee.BigIntegerField (null = False)
    group    = peewee.ForeignKeyField (MentionGroup, null = False, backref = "mention_members")
    is_owner = peewee.BooleanField    (null = False, default = False)

    @property
    def guild(self):
        return self.group.guild

class TemporaryChannel(BaseModel):
    class Status(Enum):
        pending  = 0
        accepted = 1
        denied   = 2

    class Type(Enum):
        normal = 0
        mini   = 1

    guild_id            = peewee.BigIntegerField (null = False)
    name                = EmojiField             (null = False)
    topic               = EmojiField             (null = False)
    channel_id          = peewee.BigIntegerField (null = True)
    user_id             = peewee.BigIntegerField (null = False)
    expiry_date         = peewee.DateTimeField   (null = True)
    active              = peewee.BooleanField    (null = False, default = True)
    status              = EnumField              (Status, null = False, default = Status.pending)
    deny_reason         = peewee.TextField       (null = True)
    pending_items       = peewee.IntegerField    (null = True)
    type                = EnumField              (Type, null = False, default = Type.normal)

    @property
    def item_code(self):
        if self.type == self.Type.normal:
            return "milky_way"
        elif self.type == self.Type.mini:
            return "orions_belt"

    @property
    def alias_name(self):
        if self.type == self.Type.normal:
            return "milkyway"
        elif self.type == self.Type.mini:
            return "orion"

    @property
    def days(self):
        if self.type == self.Type.normal:
            return 7
        elif self.type == self.Type.mini:
            return 1

    @property
    def ticket_embed(self):
        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.set_author(icon_url = self.user.avatar_url, name = str(self.user))

        embed.description = f"A temporary channel was requested.\nName: `{self.name}`\nTopic: `{self.topic}`"

        footer = []
        footer.append(f"Use '/{self.alias_name} deny {self.id} <reason>' to deny this request")
        footer.append(f"Use '/{self.alias_name} accept {self.id}' to accept this request")
        embed.set_footer(text = "\n".join(footer))

        return embed

    def get_topic(self):
        return f"{self.topic}\nexpires at {self.expiry_date} UTC"

    async def update_channel_topic(self):
        await self.channel.edit(topic = self.get_topic())

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
            topic = self.get_topic(),
            category = category
        )
        self.channel_id = channel.id
        return channel

class Reminder(BaseModel):
    channel_id          = peewee.BigIntegerField (null = False)
    user_id             = peewee.BigIntegerField (null = False)
    due_date            = peewee.DateTimeField   (null = False)
    text                = peewee.TextField       (null = False)
    finished            = peewee.BooleanField    (null = False, default = False)

class Earthling(BaseModel):
    user_id              = peewee.BigIntegerField  (null = False)
    guild_id             = peewee.BigIntegerField  (null = False)
    personal_role_id     = peewee.BigIntegerField  (null = True)
    human                = peewee.ForeignKeyField  (Human, column_name = "global_human_id" )
    last_active          = peewee.DateTimeField    (null = True)
    mandatory_role_warns = peewee.IntegerField     (null = False, default = 0)

    class Meta:
        indexes = (
            (('user_id', 'guild_id'), True),
        )

    @property
    def inactive(self):
        last_active = self.last_active or self.member.joined_at
        return (last_active + config.inactive_delta) < datetime.datetime.utcnow()

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
            human = config.bot.get_human(user = member)
        )

class TemporaryVoiceChannel(BaseModel):
    guild_id    = peewee.BigIntegerField  (null = False)
    channel_id  = peewee.BigIntegerField  (null = False)

    def delete_instance(self, *args, **kwargs):
        if self.channel is not None:
            asyncio.gather(self.channel.delete(reason = "Temporary VC channel removed."))
        super().delete_instance(*args, **kwargs)

class RedditAdvertisement(BaseModel):
    last_advertised = peewee.DateTimeField   (null = True)
    automatic       = peewee.BooleanField    (null = False, default = False)
    guild_id        = peewee.BigIntegerField (null = False)
    description     = peewee.TextField       (null = False)

    @property
    def available(self):
        if self.last_advertised is None:
            return True
        hours = 24
        if random.randint(0, 3) == 1:
            hours += 2
        return (self.last_advertised + datetime.timedelta(hours = hours)) < datetime.datetime.utcnow()

    async def get_invite_url(self):
        for invite in await self.guild.invites():
            if invite.max_age == 0 and invite.max_uses == 0:
                return invite.url

    async def advertise(self):
        subreddit_names = ["DiscordAdvertising", "discordservers", "DiscordAppServers"]
        subreddits = [self.bot.reddit.subreddit(x) for x in subreddit_names]
        submissions = []
        for subreddit in subreddits:
            submission = subreddit.submit(self.description, url = await self.get_invite_url())
            submissions.append(submission)
            self.last_advertised = datetime.datetime.utcnow()
        self.save()

        return submissions
