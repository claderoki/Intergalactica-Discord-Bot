import abc
from abc import ABC
from typing import Optional, TypeVar, Generic, Type

from discord.app_commands import Command

from src.models import Human, Pigeon
from src.config import config

T = TypeVar("T")


class Invertable(ABC):
    def __init__(self):
        self.inverted = False

    def invert(self):
        self.inverted = True
        return self

    @abc.abstractmethod
    def failure_message_self_inverted(self) -> str:
        pass

    @abc.abstractmethod
    def failure_message_other_inverted(self) -> str:
        pass


class Validation(ABC, Generic[T]):
    def __init__(self):
        super().__init__()
        self.failure_message_self_override: Optional[str] = None
        self.failure_message_other_override: Optional[str] = None

    @abc.abstractmethod
    def _validate(self, target: T) -> bool:
        pass

    def get_message(self, other: bool):
        func = 'failure_message_'
        func += 'other' if other else 'self'
        if isinstance(self, Invertable) and self.inverted:
            func += '_inverted'

        override = getattr(self, f'{func}_override', None)
        if override:
            return override
        if hasattr(self, f'{func}_override'):
            pass
        error = getattr(self, func)()

    @abc.abstractmethod
    def failure_message_self(self) -> str:
        pass

    @abc.abstractmethod
    def failure_message_other(self) -> str:
        pass

    @abc.abstractmethod
    def get_target_type(self) -> Type[T]:
        pass

    @abc.abstractmethod
    def find_target(self, user_id: int) -> Optional[T]:
        pass

    def validate(self, target) -> bool:
        if isinstance(self, Invertable) and self.inverted:
            return not self._validate(target)
        else:
            return self._validate(target)

    def wrap(self):
        def wrapper(func):
            def inner(f: Command):
                existing = f.extras.get('validations', [])
                existing.insert(0, self)
                f.extras['validations'] = existing
                return f

            return inner if func is None else inner(func)

        return wrapper


class HumanValidation(Validation[Human], ABC):
    def get_target_type(self):
        return Human

    def find_target(self, user_id: int) -> Optional[Human]:
        return config.bot.get_human(user=user_id)


class HasGold(HumanValidation):
    def __init__(self, amount: int):
        super().__init__()
        self.amount = amount

    def _validate(self, target: Human) -> bool:
        return target.gold >= self.amount

    def failure_message_self(self) -> str:
        return f'You do not have enough gold for this. {self.amount} needed.'

    def failure_message_other(self) -> str:
        return f'The other person does not have enough gold for this. {self.amount} needed.'


class AddHumanToTarget(HumanValidation):
    def __init__(self):
        super().__init__()

    def _validate(self, target: Human) -> bool:
        return True

    def failure_message_self(self) -> str:
        return ''

    def failure_message_other(self) -> str:
        return ''


def has_gold(amount: int):
    return HasGold(amount).wrap()


def add_human_to_target():
    return AddHumanToTarget().wrap()
