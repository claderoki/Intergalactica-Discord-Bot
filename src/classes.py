import enum

import peewee
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
                 bot: commands.Bot,
                 cache: Cache,
                 settings: Settings,
                 path: str,
                 environ: EnvironmentalVariables
                 ):
        self.bot = bot
        self.tree = bot.tree if bot else None
        self.cache = cache
        self.mode = mode
        self.settings = settings
        self.path = path
        self.environ = environ
