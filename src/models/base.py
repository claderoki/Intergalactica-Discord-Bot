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

    @property
    def guild(self):
        return self.bot.get_guild(self.guild_id)

    @property
    def user(self):
        return self.bot.get_user(self.user_id)

    @property
    def member(self):
        return self.guild.get_member(self.user_id)

    @property
    def channel(self):
        return self.guild.get_channel(self.channel_id)

    class Meta:
        database = peewee.MySQLDatabase(
            "locus_db", 
            user     = os.environ["mysql_user"],
            password = os.environ["mysql_password"],
            host     = os.environ["mysql_host"],
            port     = int(os.environ["mysql_port"]),
            
            )
        # database = peewee.SqliteDatabase(config.data_folder + "/" + "lotus_db.sqlite")


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
