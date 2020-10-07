import datetime
from enum import Enum


class Mode(Enum):
    production = 1
    development = 2


path = __file__.replace("/src/config.py", "")
path = path.replace("\\src\\config.py", "")
bot = None

xp_timeout = 120

inactive_delta = datetime.timedelta(weeks = 2)

min_xp = 10
max_xp = 20

br = "\uFEFF"