from discord.ext import commands
from src.models import Human, database

def is_tester():
    def predicate(ctx):
        with database.connection_context():
            human, _ = Human.get_or_create(user_id = ctx.author.id)
            return human.tester
    return commands.check(predicate)