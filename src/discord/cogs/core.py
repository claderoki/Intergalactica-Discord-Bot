import peewee
from discord.ext import commands

from src.discord.bot import Locus


class BaseCog(commands.Cog):
    bot: Locus = None

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @staticmethod
    def start_task(task, check: callable = lambda: True):
        if callable(check):
            check = check()

        if check:
            task.add_exception_type(peewee.OperationalError)
            task.add_exception_type(peewee.InterfaceError)
            try:
                task.start()
            except RuntimeError:
                pass
