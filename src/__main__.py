import os
import argparse

import src.config as config
from src.utils.environmental_variables import EnvironmentalVariables

parser = argparse.ArgumentParser()
parser.add_argument('--mode', default=config.Mode.development.name, choices=[x.name for x in list(config.Mode)])
parser.add_argument('--service', default="none", choices=["heroku", "none"])
args = parser.parse_args()
mode = config.Mode[args.mode]
service = args.service

if service == "heroku":
    config.environ = EnvironmentalVariables.from_environ()
else:
    path = config.path + "/env"
    try:
        config.environ = EnvironmentalVariables.from_path(path)
    except FileNotFoundError:
        EnvironmentalVariables.create_env_file(path)
        print(f"Please enter the environmental variables in the {path} file.")
        quit()

from src.discord.bot import Locus
config.bot = Locus(mode)
config.bot.heroku = service == "heroku"
config.bot.load_all_cogs()
config.bot.run(config.environ.discord_token)