import json
from enum import Enum

import emoji
import peewee
import pycountry
from discord.ext import commands

from src.config import config
from src.disc.helpers.pretty import prettify_value
from src.disc.helpers.waiters import *
from src.utils.country import Country


def rand():
    # if isinstance(config.settings.base_database, peewee.SqliteDatabase):
    return peewee.fn.Random()
    # return peewee.fn.Rand()


def order_by_random(select: peewee.ModelSelect):
    print(select.model._meta.database)
    return select.order_by(peewee.fn.Rand())


class OnSkipAction(Enum):
    ignore = 1
    null = 2
    default = 3
    exception = 4


class BaseModelSelect(peewee.ModelSelect):
    def rand(self) -> 'BaseModelSelect':
        if isinstance(self.model._meta.database, peewee.SqliteDatabase):
            rand = peewee.fn.Random()
        else:
            rand = peewee.fn.Rand()

        return self.order_by(rand)


class UnititializedModel(peewee.Model):
    @classmethod
    def select(cls, *fields) -> BaseModelSelect:
        is_default = not fields
        if not fields:
            fields = cls._meta.sorted_fields
        return BaseModelSelect(cls, fields, is_default=is_default)

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

        if isinstance(field, TimeDeltaField):
            return TimeDeltaWaiter(ctx, **kwargs)
        if isinstance(field, CountryField):
            return CountryWaiter(ctx, **kwargs)
        if isinstance(field, peewee.BooleanField):
            return BoolWaiter(ctx, **kwargs)
        if isinstance(field, EnumField):
            return EnumWaiter(ctx, field.enum, **kwargs)
        if isinstance(field, (peewee.TextField, peewee.CharField)):
            return StrWaiter(ctx, max_words=None, **kwargs)
        if isinstance(field, (peewee.IntegerField, peewee.BigIntegerField)):
            return IntWaiter(ctx, **kwargs)
        if isinstance(field, peewee.DateField):
            return DateWaiter(ctx, **kwargs)
        if isinstance(field, peewee.TimeField):
            return TimeWaiter(ctx, **kwargs)

    async def editor_for(self, ctx, attr, on_skip=OnSkipAction.ignore, waiter=None, **kwargs):
        if waiter is None:
            waiter = self.waiter_for(ctx, attr, **kwargs)

        if waiter is None:
            raise Exception(f"Waiter for type `{getattr(self.__class__, attr)}` was not found.")

        try:
            value = await waiter.wait()
            if attr == "due_date":
                value = datetime.datetime.utcnow() + value
            elif "_id" in attr and hasattr(value, "id"):
                value = value.id
            setattr(self, attr, value)
        except Skipped:
            if on_skip == OnSkipAction.null:
                setattr(self, None, await waiter.wait())
            elif on_skip == OnSkipAction.default:
                setattr(self, getattr(self.__class__, attr).default, await waiter.wait())
            elif on_skip == OnSkipAction.exception:
                raise

    @property
    def mention(self):
        if hasattr(self, "user_id"):
            return f"<@{self.user_id}>"

    @classmethod
    def get_random(cls):
        return cls.select().order_by(peewee.fn.Rand()).limit(1).first()

    @property
    def bot(self) -> commands.Bot:
        return config.bot

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(id=int(argument))


class BaseModel(UnititializedModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._member = None
        self._guild = None
        self._user = None
        self._channel = None

    @property
    def guild(self) -> discord.Guild:
        if self._guild is None:
            self._guild = self.bot.get_guild(self.guild_id)
        return self._guild

    @property
    def user(self) -> discord.User:
        if self._user is None:
            self._user = self.bot.get_user(self.user_id)
        return self._user

    @property
    def member(self) -> discord.Member:
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
        if isinstance(config.config.settings.base_database, peewee.MySQLDatabase):
            table_settings = ["DEFAULT CHARSET=utf8"]
        database = config.config.settings.base_database


class JsonField(peewee.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value)


class RangeField(peewee.TextField):
    def __init__(self, start, stop, step, **kwargs):
        range_ = range(start, stop, step)
        self.start = range_.start
        self.stop = range_.stop
        self.step = range_.step
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
            return pycountry.languages.get(alpha_2=value)


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

    def db_value(self, value: datetime.timedelta):
        if value is not None:
            return f"{int(value.total_seconds())} seconds"

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


class LongTextField(peewee.TextField):
    pass


class DiscordSnowflakeField(peewee.BigIntegerField):
    pass


class GuildIdField(DiscordSnowflakeField):
    pass


class UserIdField(DiscordSnowflakeField):
    pass


class RoleIdField(DiscordSnowflakeField):
    pass


class BaseSettings(BaseModel):
    enabled = peewee.BooleanField(null=False, default=False)


class MemberSettings(BaseSettings):
    guild_id = GuildIdField(null=False)
    user_id = UserIdField(null=False)


class UserSettings(BaseSettings):
    user_id = UserIdField(null=False)


class GuildSettings(BaseSettings):
    guild_id = GuildIdField(null=False)


class BaseProfile(BaseModel):
    pass


class UserProfile(BaseProfile):
    user_id = UserIdField(null=False)


class MemberProfile(UserProfile):
    guild_id = GuildIdField(null=False)
