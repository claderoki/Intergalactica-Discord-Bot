from discord.ext import commands


class NotSetup(commands.errors.CheckFailure): pass


class GameRunning(commands.errors.CheckFailure): pass
