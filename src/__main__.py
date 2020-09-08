# import pymysql
# pymysql.install_as_MySQLdb()

import src.config as config
from src.discord.bot import Locus

config.bot = Locus()
config.bot.run(config.token)
