import random
from typing import List

from src.config import config
import discord

class RedditHelper:
    @classmethod
    def get_random_words(cls, nsfw: bool = False, max_words: int = 10, min_length: int = 4, max_length: int = 10) -> List[str]:
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
        from src.models import Translation
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


class CapsLockCorrector:
    __slots__ = ("guild_id", "channel_ids", "user_ids")

    def __init__(self, guild_id: int, channel_ids: list, user_ids: list):
        self.guild_id = guild_id
        self.channel_ids = channel_ids
        self.user_ids = user_ids

    def should_correct(self, message: discord.Message) -> bool:
        if message.channel.id not in self.channel_ids:
            return False
        if message.author.id not in self.user_ids:
            return False

        caps_lock_count = sum(1 for x in message.content if x.isupper())
        caps_lock_percentage = (caps_lock_count / len(message.content)) * 100
        return caps_lock_percentage > 70 and len(message.content) > 10

    def __correct_content(self, content: str) -> str:
        content = content.capitalize()
        if not content.endswith('.'):
            content += '.'
        return content

    async def correct(self, message: discord.Message):
        await message.delete()
        embed: discord.Embed = discord.Embed()
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar)
        embed.description = self.__correct_content(message.content)
        await message.channel.send(embed=embed)
