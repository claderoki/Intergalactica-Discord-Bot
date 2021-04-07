from discord.ext import commands
from src.models import Human, database
import src.config as config

def is_tester():
    def predicate(ctx):
        with database.connection_context():
            human = config.bot.get_human(user = ctx.author)
            return human.tester
    return commands.check(predicate)