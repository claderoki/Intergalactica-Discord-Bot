import peewee

import src.config as config

class BaseModel(peewee.Model):

    @property
    def bot(self):
        return config.bot

    class Meta:
        database = peewee.MySQLDatabase("locus_db", **config.mysql)
        # database = peewee.SqliteDatabase(config.data_folder + "/" + "lotus_db.sqlite")
