import discord

import datetime
from enum import Enum


class Mode(Enum):
    production = 1
    development = 2


environ = None
path = __file__.replace("\\", "/").replace("/src/config.py", "")
bot = None
tree: discord.app_commands.CommandTree = None
inactive_delta = datetime.timedelta(weeks=2)
xp_timeout = 120
min_xp = 10
max_xp = 20
br = "\uFEFF"


class Cache:
    def __init__(self):
        self.cache = dict()

    def __hash_func_call(self, func, args, kwargs) -> str:
        return str(hash(func.__name__) + hash(args) + hash(kwargs))

    def result(self, func):
        def decorator(*args, **kwargs):
            hash = self.__hash_func_call(func, args, kwargs)
            cached = self.cache.get(hash)
            if cached is not None:
                return cached
            result = func(*args)
            self.cache[hash] = result
            return result
        return decorator


cache = Cache()
