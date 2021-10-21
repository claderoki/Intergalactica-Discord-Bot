import praw

class PrawInstanceCache:
    __slots__  = ()
    _instances = {}

    @classmethod
    def cache(cls, identifier: int, instance: praw.reddit.Reddit):
        cls._instances[identifier] = instance

    @classmethod
    def get(cls, identifier) -> praw.reddit.Reddit:
        return cls._instances.get(identifier)