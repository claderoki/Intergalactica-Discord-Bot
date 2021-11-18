import os
import json

import peewee
import pycountry
import emoji

from src.discord.helpers.waiters import *
from src.discord.helpers.pretty import prettify_value
from src.utils.country import Country
import src.config as config

class BaseModel(peewee.Model):

    @classmethod
    def pluck(cls, attr):
        query = cls.select(getattr(cls, attr))
        return tuple([getattr(x, attr) for x in query])

    def waiter_for(self, ctx, attr, **kwargs):
        cls = self.__class__
        field = getattr(cls, attr)
        value = getattr(self, attr)

        if "prompt" not in kwargs:
            kwargs["prompt"] = ctx.translate(f"{peewee.make_snake_case(cls.__name__)}_{attr}_prompt")
            if "due_date" not in attr:
                if field.default is not None:
                    kwargs["prompt"] += f"\nDefault: **{prettify_value(field.default)}**"
                if value is not None and value != "":
                    kwargs["prompt"] += f"\nCurrent: **{prettify_value(value)}**"

        if "skippable" not in kwargs:
            kwargs["skippable"] = field.null or field.default is not None

        if attr == "timezone":
            return TimezoneWaiter(ctx, **kwargs)
        if "channel_id" in attr:
            return TextChannelWaiter(ctx, **kwargs)
        if "user_id" in attr:
            return MemberWaiter(ctx, **kwargs)
        if "role_id" in attr:
            return RoleWaiter(ctx, **kwargs)
        if attr == "due_date":
            return TimeDeltaWaiter(ctx, **kwargs)
        if attr == "image_url":
            AttachmentWaiter(ctx, **kwargs)

        if isinstance(field, CountryField):
            return CountryWaiter(ctx, **kwargs)
        if isinstance(field, peewee.BooleanField):
            return BoolWaiter(ctx, **kwargs)
        if isinstance(field, EnumField):
            return EnumWaiter(ctx, field.enum, **kwargs)
        if isinstance(field, (peewee.TextField, peewee.CharField)):
            return StrWaiter(ctx, max_words = None, **kwargs)
        if isinstance(field, (peewee.IntegerField, peewee.BigIntegerField)):
            return IntWaiter(ctx, **kwargs)
        if isinstance(field, peewee.DateField):
            return DateWaiter(ctx, **kwargs)
        if isinstance(field, peewee.TimeField):
            return TimeWaiter(ctx, **kwargs)

    async def editor_for(self, ctx, attr, on_skip = "pass", waiter = None, **kwargs):
        if waiter is None:
            waiter = self.waiter_for(ctx, attr, **kwargs)

        if waiter is None:
            raise Exception(f"Waiter for type `{getattr(self.__class__, attr)}` was not found.")

        try:
            value = await waiter.wait()
            if attr == "due_date":
                value = datetime.datetime.utcnow() + value
            elif "_id" in attr:
                value = value.id
            setattr(self, attr, value)
        except Skipped:
            if on_skip in ("null", "none"):
                setattr(self, None, await waiter.wait())
            elif on_skip == "default":
                setattr(self, getattr(self.__class__, attr).default, await waiter.wait())
            elif on_skip == "raise":
                raise

    @property
    def mention(self):
        if hasattr(self, "user_id"):
            return f"<@{self.user_id}>"

    @classmethod
    def get_random(cls):
        return cls.select().order_by(peewee.fn.Rand()).limit(1).first()

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
            self._channel = self.bot.get_channel(self.channel_id)
        return self._channel

    class Meta:
        legacy_table_names = False
        only_save_dirty = True
        table_settings = ["DEFAULT CHARSET=utf8"]
        database = peewee.MySQLDatabase(
            config.environ["mysql_db_name"],
            user     = config.environ["mysql_user"],
            password = config.environ["mysql_password"],
            host     = config.environ["mysql_host"],
            port     = int(config.environ["mysql_port"])
        )

class JsonField(peewee.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value)

class RangeField(peewee.TextField):
    def __init__(self, start, stop, step, **kwargs):
        range_     = range(start, stop, step)
        self.start = range_.start
        self.stop  = range_.stop
        self.step  = range_.step
        super().__init__(**kwargs)

    def db_value(self, value):
        if value:
            return f"{self.start},{self.stop},{self.step}"

    def python_value(self, value):
        if value:
            return range(*value.split(","))

class ArrayField(peewee.TextField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def db_value(self, value):
        if value:
            return ";".join(x for x in value if x is not None)

    def python_value(self, value):
        if value:
            return [x for x in value.split(";")]
        else:
            return []

class LanguageField(peewee.TextField):
    def db_value(self, value):
        if value is not None:
            return value.alpha_2

    def python_value(self, value):
        if value is not None:
            return pycountry.languages.get(alpha_2 = value)

class CountryField(peewee.TextField):
    def db_value(self, value):
        if value is not None:
            return value.iso()["alpha2"]

    def python_value(self, value):
        if value is not None:
            return Country.from_alpha_2(value)

class TimeDeltaField(peewee.TextField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def db_value(self, value):
        if value is not None:
            return f"{value.seconds} seconds"

    def python_value(self, value):
        if value is not None:
            return TimeDeltaWaiter._convert(value)

class EnumField(peewee.TextField):
    def __init__(self, enum, **kwargs):
        self.enum = enum
        super().__init__(**kwargs)

    def db_value(self, value):
        if value is not None:
            return value.name

    def python_value(self, value):
        if value is not None:
            return self.enum[value]

class UnicodeField(peewee.CharField):
    def db_value(self, value):
        if value is not None:
            return value.encode("utf8")

    def python_value(self, value):
        if value is not None:
            return value.decode()

class EmojiField(peewee.TextField):
    def db_value(self, value):
        if value is not None:
            return emoji.demojize(value)

    def python_value(self, value):
        if value is not None:
            return emoji.emojize(value)

class PercentageField(peewee.IntegerField):
    def db_value(self, value):
        if value is not None:
            return max(min(value, 100), 0)