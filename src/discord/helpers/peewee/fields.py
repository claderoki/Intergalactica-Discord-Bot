import json

import peewee
import emoji

import src.config as config


class JsonField(peewee.TextField):

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value)

class EnumField(peewee.TextField):
    def __init__(self, enum, **kwargs):
        self.enum = enum
        super().__init__(**kwargs)

    def db_value(self, value):
        return value.name

    def python_value(self, value):
        return self.enum[value]
    

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
        if isinstance(value, int):
            return value
            
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
