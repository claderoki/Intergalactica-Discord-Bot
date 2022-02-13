import asyncio
from enum import Enum

import discord

from src.discord.helpers.waiters.base import StrWaiter
from src.models import UserSetting


class ValidationResult:
    __slots__ = ("errors",)

    def __init__(self):
        self.errors = []

    def add_error(self, message: str):
        self.errors.append(message)

    def is_ok(self) -> bool:
        return len(self.errors) == 0


class UserSettingModel:
    example = None
    symbol = None

    class BaseType(Enum):
        string = 1
        integer = 2

    __slots__ = ("human_id", "value")

    def db_value(self, value):
        return value

    def python_value(self, value):
        return value

    @classmethod
    def get_or_none(cls, human):
        db_setting = UserSetting.get_or_none(human=human, code=cls.code)
        if db_setting is None:
            return None
        return cls(human_id=human.id, value=db_setting.value)

    def save(self):
        value = self.db_value(self.value)
        (UserSetting
         .insert(human=self.human_id, code=self.code, value=value)
         .on_conflict(update={UserSetting.value: value})
         .execute())

    def get_waiter_kwargs() -> dict:
        return None

    @classmethod
    async def wait(cls, ctx, **kwargs) -> "UserSettingModel":
        human = ctx.bot.get_human(user=ctx.message.author)
        waiter = UserSettingModelWaiter(ctx, cls, human.id, prompt=ctx.translate(cls.code + "_prompt"), **kwargs)
        model = await waiter.wait()
        return model

    def sanitize(self):
        pass

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "validate"):
            raise Exception("You do not have the validate method implemented.")

        # if not hasattr(cls, "code"):
        #     raise Exception("You do not have the code attribute implemented.")

        if not hasattr(cls, "type"):
            raise Exception("You do not have the type attribute implemented.")

    def base_validation(self) -> ValidationResult:
        return ValidationResult()

    def __init__(self, human_id: int, value):
        self.human_id = human_id
        self.value = self.python_value(value)


class UserSettingModelWaiter(StrWaiter):
    def __init__(self, ctx, setting_class, human_id, **kwargs):
        waiter_kwargs = setting_class.get_waiter_kwargs()
        if waiter_kwargs is not None:
            super().__init__(ctx, **waiter_kwargs, **kwargs)
        else:
            super().__init__(ctx, **kwargs)

        self.setting_class = setting_class
        self.human_id = human_id

    @property
    def instructions(self):
        return self.setting_class.example

    def convert(self, argument):
        model = self.setting_class(self.human_id, argument)
        model.sanitize()
        return model

    def check(self, message):
        if not super().check(message):
            return False

        result = self.converted.validate()
        if not result.is_ok():
            embed = discord.Embed(color=discord.Color.red())
            embed.title = "Invalid value"
            embed.add_field(name="Errors", value="\n".join(result.errors), inline=False)
            embed.set_footer(text="Try again.")
            asyncio.gather(message.channel.send(embed=embed))
            return False
        else:
            return True
