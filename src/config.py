import discord

import datetime
from enum import Enum


class Mode(Enum):
    production = 1
    development = 2


environ = None

path = __file__.replace("\\", "/").replace("/src/config.py", "")

bot = None


tree: discord.app_commands.CommandTree = None

inactive_delta = datetime.timedelta(weeks=2)

xp_timeout = 120
min_xp = 10
max_xp = 20

br = "\uFEFF"
