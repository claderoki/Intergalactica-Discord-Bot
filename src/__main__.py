import argparse
import os
import sys

import peewee

import src.config as config
from src.classes import Mode, Cache, Settings
from src.utils.environmental_variables import EnvironmentalVariables

parser = argparse.ArgumentParser()
parser.add_argument('--mode', default=Mode.development.name, choices=[x.name for x in list(Mode)])
parser.add_argument('--sqlite', default='0', choices=['0', '1'])
parser.add_argument('--restarted', default='0', choices=['0', '1'])

args = parser.parse_args()
mode = Mode[args.mode]
restarted = args.restarted == '1'
sqlite = args.sqlite == '1'


def init_environ() -> EnvironmentalVariables:
    path = config.path + "/.env"
    try:
        return EnvironmentalVariables.from_path(path)
    except FileNotFoundError:
        EnvironmentalVariables.create_env_file(path)
        print(f"Please enter the environmental variables in the {path} file.")
        quit()


def create_database(database_name: str) -> peewee.Database:
    if args.sqlite == '1':
        return peewee.SqliteDatabase(f'data/{database_name}.sqlite')
    return peewee.MySQLDatabase(
        database_name,
        user=config.environ["mysql_user"],
        password=config.environ["mysql_password"],
        host=config.environ["mysql_host"],
        port=int(config.environ["mysql_port"])
    )


environ = init_environ()
config.init(mode, environ, None, Cache(),
            Settings(create_database(environ["mysql_db_name"]), create_database('birthday_db')))

from src.disc.bot import Locus

locus = Locus(config.config)

config.init(mode, environ, locus, Cache(), Settings(
    create_database(environ["mysql_db_name"]),
    create_database('birthday_db')
))

config.config.bot.restarted = restarted
config.config.bot.run(config.environ.discord_token_dev)

args = ["-m", "src"]

for arg in sys.argv[1:]:
    args.append(arg)

if config.config.bot.restarting:
    args.append(f"--restarted=1")
    os.execl(sys.executable, os.path.abspath(config.path), *args)
