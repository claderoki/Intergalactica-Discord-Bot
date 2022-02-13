import discord


class ValidationContext:
    __slots__ = ("member", "user", "message", "channel", "guild")

    def __init__(self):
        pass

    @classmethod
    def from_message(cls, message: discord.Message):
        obj = cls()
        if isinstance(message.channel, discord.DMChannel):
            obj.user = message.author
        else:
            obj.member = message.author
            obj.user = message.author
            obj.guild = message.guild
            obj.message = message
        return obj
