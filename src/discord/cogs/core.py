from discord.ext import commands

class BaseCog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def start_task(self, task, check = True):
        if callable(check):
            check = check()

        if check:
            task.task()