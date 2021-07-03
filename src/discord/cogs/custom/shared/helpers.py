from enum import Enum

from src.discord.helpers.embed import Embed

class GuildHelper:
    __slots__ = ()

    @classmethod
    async def get_invite_url(cls, guild) -> str:
        """Gets the first unlimited invite url for the specified guild, or None if there aren't any."""
        for invite in await guild.invites():
            if invite.max_age == 0 and invite.max_uses == 0:
                return invite.url

class Logger:
    __slots__ = ("sendable", )

    class Type(Enum):
        warning = 0
        success = 1
        error   = 2

    def __init__(self, sendable):
        self.sendable = sendable

    def __bool__(self):
        return self.sendable is not None

    async def log(self, content = None, type: Type = Type.success, **kwargs):
        try:
            embed = getattr(Embed, type.name)(content)
            await self.sendable.send(embed = embed)
        except:
            pass