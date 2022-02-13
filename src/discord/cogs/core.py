import peewee
from discord.ext import commands


class BaseCog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def start_task(self, task, check=True):
        if callable(check):
            check = check()

        if check:
            task.add_exception_type(peewee.OperationalError)
            task.add_exception_type(peewee.InterfaceError)
            # task.add_exception_type(client_exceptions.ServerDisconnectedError)
            try:
                task.start()
            except RuntimeError:
                pass
