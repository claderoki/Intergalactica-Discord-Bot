import datetime
import discord

from src.models import InactiveChannelsSettings

class InactiveChannelsRepository:
    @classmethod
    def get_settings(cls, guild_id: int) -> InactiveChannelsSettings:
        return InactiveChannelsSettings.get_or_none(guild_id = guild_id)

class InactiveChannelsHelper:
    @classmethod
    async def is_inactive(cls, channel: discord.TextChannel, settings: InactiveChannelsSettings) -> bool:
        after = datetime.datetime.utcnow() - settings.timespan
        count = 0
        async for _ in channel.history(limit = settings.max_messages, after = after):
            count += 1
        return count < settings.max_messages