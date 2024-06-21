from __future__ import annotations
import enum

import peewee
from discord import app_commands
from discord.ext import commands

from src.utils.environmental_variables import EnvironmentalVariables


class Cache:
    def __init__(self):
        self.cache = dict()

    def __hash_func_call(self, func, args, kwargs) -> str:
        return str(hash(func.__name__) + hash(args) + hash(frozenset(kwargs)))

    def __call__(self, category=None):
        def wrapper(func):
            def decorator(*args, **kwargs):
                hash = self.__hash_func_call(func, args, kwargs)
                cached = self.cache.get(hash)
                if cached is not None:
                    return cached
                result = func(*args, **kwargs)
                self.cache[hash] = result
                return result

            return decorator

        return wrapper


class Settings:
    def __init__(self, base_database: peewee.Database, birthday_database: peewee.Database):
        self.base_database = base_database
        self.birthday_database = birthday_database


class Mode(enum.Enum):
    production = 1
    development = 2


class Config:
    def __init__(self,
                 mode: Mode,
                 cache: Cache,
                 settings: Settings,
                 path: str,
                 environ: EnvironmentalVariables
                 ):
        self.cache = cache
        self.tree: app_commands.CommandTree = None
        self._bot: 'src.disc.bot.Locus' = None
        self.mode = mode
        self.settings = settings
        self.path = path
        self.environ = environ
        self.create_test = False

    @property
    def bot(self):
        return self._bot

    @bot.setter
    def bot(self, bot: commands.Bot):
        self._bot = bot
        self.tree = bot.tree if bot else None
