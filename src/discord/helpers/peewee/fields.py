import json

import peewee
import emoji

import src.config as config


class JsonField(peewee.TextField):

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value)


class EmojiField(peewee.TextField):

    def db_value(self, value):
        return emoji.demojize(value)

    def python_value(self, value):
        return emoji.emojize(value)

class DiscordField(peewee.BigIntegerField):

    @property
    def bot(self):
        return config.bot

    def db_value(self, value):
        return value.id


class UserField(DiscordField):
    
    def python_value(self, value):
        return self.bot.get_user(value)

class GuildField(DiscordField):
    
    def python_value(self, value):
        return self.bot.get_guild(value)


class ChannelField(DiscordField):

    def python_value(self, value):
        return self.bot.get_channel(value)
