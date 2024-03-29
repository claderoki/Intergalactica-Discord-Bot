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

    @abc.abstractmethod
    def _validate(self, target: T) -> bool:
        pass

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


class PigeonValidation(Validation[Pigeon], ABC):
    def get_target_type(self):
        return Pigeon

    def find_target(self, user_id: int) -> Optional[Pigeon]:
        from src.disc.commands.pigeon.helpers import PigeonHelper
        return PigeonHelper().get_pigeon(user_id)


class HasPigeon(PigeonValidation, Invertable):
    def _validate(self, target: Pigeon) -> bool:
        return target is not None

    def failure_message_self(self) -> str:
        return 'You do not have a pigeon.'

    def failure_message_other(self) -> str:
        return 'The other person does not have a pigeon.'

    def failure_message_self_inverted(self) -> str:
        return 'You already have a pigeon.'

    def failure_message_other_inverted(self) -> str:
        return 'The other person already has a pigeon.'


class HasStatus(PigeonValidation):
    def __init__(self, status: Pigeon.Status):
        super().__init__()
        self.status = status

    def _validate(self, target: Pigeon) -> bool:
        return target.status == self.status

    def failure_message_self(self) -> str:
        return f'Your pigeon needs to be {self.status} to perform this action.'

    def failure_message_other(self) -> str:
        return f'The other persons pigeon needs to be {self.status} to perform this action.'


class StatLessThan(PigeonValidation):
    def __init__(self, name: str, value: int):
        super().__init__()
        self.name = name
        self.value = value

    def _validate(self, target: Pigeon) -> bool:
        value = getattr(target, self.name)
        return value < self.value

    def failure_message_self(self) -> str:
        return f'Your pigeon needs to have under {self.value} {self.name} for this action'

    def failure_message_other(self) -> str:
        return f'The other persons pigeon needs to have under {self.value} {self.name} for this action'


def food_less_than(value: int):
    return StatLessThan('food', value).wrap()


def cleanliness_less_than(value: int):
    return StatLessThan('cleanliness', value).wrap()


def health_less_than(value: int):
    return StatLessThan('health', value).wrap()


def happiness_less_than(value: int):
    return StatLessThan('happiness', value).wrap()


def has_status(status: Pigeon.Status):
    return HasStatus(status).wrap()


def has_pigeon():
    return HasPigeon().wrap()


def does_not_have_pigeon():
    return HasPigeon().invert().wrap()


def has_gold(amount: int):
    return HasGold(amount).wrap()


def add_human_to_target():
    return AddHumanToTarget().wrap()
