import peewee

from src.config import config
from src.models.base import UninitialisedModel


class SqliteBaseModel(UninitialisedModel):
    class Meta:
        legacy_table_names = False
        only_save_dirty = True
        table_settings = ["DEFAULT CHARSET=utf8"]
        database = config.settings.birthday_database


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
