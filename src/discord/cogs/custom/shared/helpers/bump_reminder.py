import datetime
import asyncio

import discord

from src.discord.helpers.known_guilds import KnownGuild
import src.config as config

class DisboardBumpReminderContext:
    __slots__ = ("guild_id", "channel_id", "available_at", "role_id")

    def __init__(self, guild_id: int, channel_id: int, available_at: datetime, role_id: int = None):
        self.guild_id     = guild_id
        self.channel_id   = channel_id
        self.available_at = available_at
        self.role_id      = role_id

    def __str__(self):
        return ", ".join(f"{x} => {getattr(self, x)}" for x in self.__slots__)

    def __repr__(self):
        return str(self)

class DisboardBumpReminder:
    _bump_cache      = {}
    _bot_id          = 302050872383242240
    _cmd             = "!d bump"
    _default_minutes = 120

    __slots__ = ("message", )

    @classmethod
    def is_eligible(cls, message: discord.Message):
        return message.guild is not None and message.content.lower().startswith(cls._cmd)

    @classmethod
    async def __wait_for_minutes(cls, message) -> int:
        try:
            disboard_response = await config.bot.wait_for("message", check = lambda x : x.author.id == cls._bot_id and x.channel.id == message.channel.id, timeout = 30)
        except asyncio.TimeoutError:
            return cls._default_minutes
        embed = disboard_response.embeds[0]
        text = embed.description
        if "minutes until the server can be bumped" in text:
            return int([x for x in text.split() if x.isdigit()][0])
        else:
            return cls._default_minutes

    @classmethod
    async def recheck_minutes(cls, message: discord.Message):
        minutes = await cls.__wait_for_minutes(message)
        cls.cache(message.guild.id, message.channel.id, minutes)

    @classmethod
    def cache(cls, guild_id: int, channel_id: int, minutes_left: int = _default_minutes):
        available_at = datetime.datetime.utcnow() + datetime.timedelta(minutes = minutes_left)

        role_id = None
        if guild_id == KnownGuild.mouse:
            #TODO: hard coded id
            role_id = 810864493642907669

        cls._bump_cache[guild_id] = DisboardBumpReminderContext(guild_id, channel_id, available_at, role_id)

    @classmethod
    def get_available_bumps(cls) -> iter:
        for _, context in cls._bump_cache.items():
            if context.available_at <= datetime.datetime.utcnow():
                yield context
