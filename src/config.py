from getpass import getuser
import pathlib
from enum import Enum
import argparse
import os
import json

class Mode(Enum):
    production = 1
    development = 2

parser = argparse.ArgumentParser(description='Choose the mode.')
parser.add_argument('--mode', default="development", choices=("development", "production") )
args = parser.parse_args()
mode = Mode[args.mode]

production = mode == Mode.production
bot_name = "lotus"

# data_folder = f"{pathlib.Path.home()}/.discord_data/" + bot_name
path = __file__.replace("/src/config.py", "")

bot = None

print("--------------------")
print(f"Bot={bot_name}")
print(f"User={getuser()}")
print(f"Mode={mode.name}")
print(f"Path={path}")
print("--------------------")

if production:
    envs = os.environ
else:
    try:
        with open(path + "/envs.json") as f:
            envs = json.loads(f.read())
    except:
        with open(path + "/envs.json", "w") as f:
            envs = {}
            for var in ("mysql_user", "mysql_password", "mysql_port", "mysql_host", "discord_token", "owm_key"):
                envs[var] = ""
            json.dump(envs, f, indent = 4)
        raise Exception("Please fill in envs.json.")


mysql = {}
for var in ("user", "password", "port", "host"):
    value = envs["mysql_" + var]
    
    if var == "port":
        value = int(value)
    
    mysql[var] = value
    

token = envs["discord_token"]
owm_key = envs["owm_key"]

xp_timeout = 120

min_xp = 10
max_xp = 20