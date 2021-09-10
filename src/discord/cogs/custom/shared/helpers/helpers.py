from enum import Enum

import discord

import src.config as config
from src.discord.helpers.embed import Embed

class GuildHelper:
    __slots__ = ()

    @classmethod
    async def get_invite_url(cls, guild) -> str:
        """Gets the first unlimited invite url for the specified guild, or None if there aren't any."""
        for invite in await guild.invites():
            if invite.max_age == 0 and invite.max_uses == 0:
                return invite.url

class ChannelHelper:
    __slots__ = ()

    @classmethod
    async def cleanup_channel(cls, channel: discord.TextChannel, log_channel: discord.TextChannel = None):
        """Clears messages from users no longer in the guild."""
        if channel is None:
            return

        tasks = []
        total_messages = 0
        messages_to_remove = []
        async for introduction in channel.history(limit=200):
            if isinstance(introduction.author, discord.User):
                messages_to_remove.append(introduction)
            total_messages += 1

        if len(messages_to_remove) >= (total_messages//2):
            return
        for introduction in messages_to_remove:
            if log_channel is not None:
                embed = discord.Embed(
                    color = config.bot.get_dominant_color(),
                    title = f"Purged: Introduction by {introduction.author}",
                    description = introduction.content
                )
                tasks.append(log_channel.send(embed = embed))
            tasks.append(introduction.delete())

        asyncio.gather(*tasks)
