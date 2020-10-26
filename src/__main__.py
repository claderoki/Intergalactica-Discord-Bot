import os
import argparse

import src.config as config

parser = argparse.ArgumentParser(description='Choose the mode.')
parser.add_argument('--mode', default="development", choices=[x.name for x in list(config.Mode)])
args = parser.parse_args()
mode = config.Mode[args.mode]

parser = argparse.ArgumentParser(description='Choose the mode.')
parser.add_argument('--service', default="none", choices=["heroku", "none"])
args = parser.parse_args()
service = args.service


if service != "heroku":
    try:
        with open(config.path + "/env") as f:
            for line in f.read().splitlines():
                key, value = line.split("=")
                os.environ[key] = value
    except FileNotFoundError:
        with open(config.path + "/env", "w") as f:
            lines = []
            for var in ("mysql_user", "mysql_password", "mysql_port", "mysql_host", "discord_token", "owm_key"):
                lines.append(f"{var}=")
            f.write("\n".join(lines))
        raise Exception("Please fill in the 'env' file.")


from src.discord.bot import Locus
config.bot = Locus(mode)
config.bot.run(os.environ["discord_token"])