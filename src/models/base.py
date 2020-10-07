import os
import json

import peewee
import emoji

import src.config as config

class BaseModel(peewee.Model):

    @property
    def bot(self):
        return config.bot

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(id = int(argument))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._member = None
        self._guild = None
        self._user = None
        self._channel = None


    @property
    def guild(self):
        if self._guild is None:
            self._guild = self.bot.get_guild(self.guild_id)
        return self._guild


    @property
    def user(self):
        if self._user is None:
            self._user = self.bot.get_user(self.user_id)
        return self._user

    @property
    def member(self):
        if self._member is None:
            self._member = self.guild.get_member(self.user_id)
        return self._member

    @property
    def channel(self):
        if self._channel is None:
            self._channel = self.guild.get_channel(self.channel_id)
        return self._channel

    class Meta:
        database = peewee.MySQLDatabase(
            "locus_db",
            user     = os.environ["mysql_user"],
            password = os.environ["mysql_password"],
            host     = os.environ["mysql_host"],
            port     = int(os.environ["mysql_port"])
        )

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
