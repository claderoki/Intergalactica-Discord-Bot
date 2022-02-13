from discord.ext import commands

import src.config as config
from src.models import database


class SpecificGuildOnly(commands.errors.CheckFailure):
    def __init__(self, guild_id):
        super().__init__(f"This command can only be used in guild `{guild_id}`")


def specific_guild_only(guild_id):
    def predicate(ctx):
        if not ctx.guild or ctx.guild.id != guild_id:
            raise SpecificGuildOnly(guild_id)
        return True

    return commands.check(predicate)


def is_tester():
    def predicate(ctx):
        with database.connection_context():
            human = config.bot.get_human(user=ctx.author)
            return human.tester

    return commands.check(predicate)
