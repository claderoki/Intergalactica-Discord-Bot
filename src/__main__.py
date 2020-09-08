import pymysql
pymysql.install_as_MySQLdb()

from src.discord.bot import Locus
import src.config as config

config.bot = Locus()
config.bot.run(config.token)
