from getpass import getuser
import pathlib
from enum import Enum
import argparse

class Mode(Enum):
    production = 1
    development = 2

parser = argparse.ArgumentParser(description='Choose the mode.')
parser.add_argument('--mode', default="development", choices=("development", "production") )
args = parser.parse_args()
mode = Mode[args.mode]

bot_name = "lotus"

# data_folder = f"{pathlib.Path.home()}/.discord_data/" + bot_name
path = __file__.replace("/src/config.py", "")


pi = getuser() == "pi"

bot = None

print("--------------------")
print(f"Bot={bot_name}")
print(f"User={getuser()}")
print(f"Mode={mode.name}")
print(f"Path={path}")
print("--------------------")

mysql = \
{
    "user"      : "Claderoki",
    "password"  : "V9nx4NS23ZYAyj",
    "port"      : 3306,
    "host"      : "84.28.180.239"
}

token = "NzQyMzY1OTIyMjQ0OTUyMDk1.XzFEJA.CmH62ICHvPcQPk_Vav7OQKgCEDE"
owm_key = "ab9a9e95335043c2afb67f9a576c38b4"


xp_timeout = 120

min_xp = 10
max_xp = 20