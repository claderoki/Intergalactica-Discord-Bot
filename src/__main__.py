import argparse
import os.path

import peewee

from src.disc.bot import Locus
from src import config
from src.classes import Mode, Cache, Settings, Config
from src.utils.environmental_variables import EnvironmentalVariables

parser = argparse.ArgumentParser()
parser.add_argument('--mode', default=Mode.development.name, choices=[x.name for x in list(Mode)])
parser.add_argument('--sqlite', default='0', choices=['0', '1'])

args = parser.parse_args()
mode = Mode[args.mode]
sqlite = args.sqlite == '1'

PATH = __file__.replace("\\", "/").replace("/src/__main__.py", "")


def init_environ() -> EnvironmentalVariables:
    path = PATH + "/.env"
    try:
        return EnvironmentalVariables.from_path(path)
    except FileNotFoundError:
        EnvironmentalVariables.create_env_file(path)
        print(f"Please enter the environmental variables in the {path} file.")
        quit()


def create_database(environ: EnvironmentalVariables, database_name: str) -> peewee.Database:
    if sqlite:
        db = peewee.SqliteDatabase(f'data/{database_name}.sqlite')
        return db
    return peewee.MySQLDatabase(
        database_name,
        user=environ["mysql_user"],
        password=environ["mysql_password"],
        host=environ["mysql_host"],
        port=int(environ["mysql_port"]),
        charset='utf8mb4'
    )


environ = init_environ()
config.config = Config(
    mode,
    Cache(),
    Settings(create_database(environ, environ["mysql_db_name"]), create_database(environ, 'birthday_db')),
    PATH,
    environ,
)
if sqlite and not os.path.exists('data/_data_created'):
    config.config.create_test = True
    with open('data/_data_created', 'w') as f:
        f.write('1')

bot = Locus(config.config)
Locus.instance.run(environ.discord_token)
