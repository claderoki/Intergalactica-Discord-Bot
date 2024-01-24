from discord.ext import commands

from src.classes import Cache, Settings, Config, Mode
from src.utils.environmental_variables import EnvironmentalVariables

environ: EnvironmentalVariables
path = __file__.replace("\\", "/").replace("/src/config.py", "")
bot: commands.Bot
config: 'Config'


def init(mode: Mode, _environ: EnvironmentalVariables, _bot: commands.Bot, cache: Cache, settings: Settings):
    global bot, environ, config
    bot = _bot
    environ = _environ
    config = Config(mode, bot, cache, settings, path, _environ)
