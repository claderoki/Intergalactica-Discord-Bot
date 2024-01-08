import discord


class Embed:
    @classmethod
    def warning(cls, message):
        return discord.Embed(description=message, color=discord.Color.red())

    @classmethod
    def error(cls, message):
        return discord.Embed(description=message, color=discord.Color.red())

    @classmethod
    def success(cls, message):
        return discord.Embed(description=message, color=discord.Color.green())
