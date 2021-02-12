from discord.ext import commands
from src.models import Human, database

def is_tester():
    def predicate(ctx):
        with database.connection_context():
            human = ctx.get_human()
            return human.tester
    return commands.check(predicate)