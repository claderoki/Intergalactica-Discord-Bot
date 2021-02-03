from discord.ext import commands
import peewee

class BaseCog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def start_task(self, task, check = True):
        if callable(check):
            check = check()

        if check:
            self.start.add_exception_type(peewee.OperationalError)
            self.start.add_exception_type(peewee.InterfaceError)
            task.task()