from getpass import getuser
import pathlib
from enum import Enum
# import subprocess

class Mode(Enum):
    production = 1
    dev_home   = 2
    dev_remote = 3


bot_name = "lotus"

data_folder = f"{pathlib.Path.home()}/.discord_data/" + bot_name
path = __file__.replace("/src/config.py", "")

token = "NzQyMzY1OTIyMjQ0OTUyMDk1.XzFEJA.CmH62ICHvPcQPk_Vav7OQKgCEDE"

pi = getuser() == "pi"

bot = None

print(getuser())

if pi:
    mode = Mode.production
else:
    mode = Mode.dev_remote

hosts = {
    Mode.production : "127.0.0.1",
    Mode.dev_home   : "192.168.1.12",
    Mode.dev_remote : "84.28.180.239"
}

mysql = \
{
    "user"      : "Claderoki",
    "password"  : "V9nx4NS23ZYAyj",
    "port"      : 3306,
    "host"      : hosts[mode]
}

owm_key = "ab9a9e95335043c2afb67f9a576c38b4"


xp_timeout = 120

min_xp = 10
max_xp = 20