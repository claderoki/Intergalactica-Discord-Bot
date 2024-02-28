from discord.app_commands import Command


def extras(key: str, value):
    def wrapper(func):
        def inner(f: Command):
            f.extras[key] = value
            return f

        return inner if func is None else inner(func)

    return wrapper
