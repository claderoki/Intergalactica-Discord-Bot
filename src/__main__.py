import os
import argparse

import src.config as config
from src.discord.bot import Locus

parser = argparse.ArgumentParser(description='Choose the mode.')
parser.add_argument('--mode', default="development", choices=[x.name for x in list(Locus.Mode)])
args = parser.parse_args()
mode = Locus.Mode[args.mode]


config.bot = Locus(mode)
config.bot.run(os.environ["discord_token"])