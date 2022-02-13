import random
from typing import List

import src.config as config
from src.models import Translation


class RedditHelper:
    @classmethod
    def get_random_words(cls, nsfw: bool = False, max_words: int = 10, min_length: int = 4, max_length: int = 10) -> \
    List[str]:
        reddit = config.bot.reddit

        word_count = 0
        while word_count < max_words:
            sub = reddit.random_subreddit(nsfw=nsfw)

            title_words = []
            for post in sub.random_rising(limit=3):
                for word in post.title.split():
                    title_words.append(word.lower())

            random.shuffle(title_words)

            for word in filter(lambda x: x.isalpha() and len(x) in range(min_length, max_length), title_words):
                yield word.lower()
                word_count += 1
                if word_count >= max_words:
                    break


class Translator:
    _translations = {}
    _missing = {}

    @classmethod
    def translate(cls, key, locale) -> str:
        cache = cls._translations.setdefault(locale, {})
        translation = cache.get(key)
        if translation is not None:
            return translation

        try:
            translation = Translation.get(locale=locale, message_key=key)
            cache[key] = translation.value
            return translation.value
        except Translation.DoesNotExist:
            cls.get_missing(locale).add(key)
            return key

    @classmethod
    def get_missing(cls, locale) -> set:
        return cls._missing.setdefault(locale, set())
