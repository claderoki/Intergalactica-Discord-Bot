import peewee

import src.config as config
from src.models.base import UnititializedModel


class SqliteBaseModel(UnititializedModel):
    class Meta:
        legacy_table_names = False
        only_save_dirty = True
        table_settings = ["DEFAULT CHARSET=utf8"]
        database = config.config.settings.birthday_database


class Person(SqliteBaseModel):
    first_name = peewee.TextField(null=True)
    last_name = peewee.TextField(null=True)
    nickname = peewee.TextField(null=False)


class Birthday(SqliteBaseModel):
    year = peewee.IntegerField(null=True)
    month = peewee.IntegerField(null=False)
    day = peewee.IntegerField(null=False)
    person = peewee.ForeignKeyField(Person, null=False)


class BirthdayReminder(SqliteBaseModel):
    year = peewee.IntegerField(null=False)
    birthday = peewee.ForeignKeyField(Birthday, null=False)
