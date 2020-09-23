import os

import peewee

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
