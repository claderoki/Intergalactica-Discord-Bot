import abc
from abc import ABC
from typing import Optional, TypeVar, Generic, Type

from src.models import Human, Pigeon
from src.config import config


T = TypeVar("T")


class Validation(ABC, Generic[T]):
    def __init__(self):
        self._inverted = False

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
        if self._inverted:
            return not self._validate(target)
        else:
            return self._validate(target)

    def invert(self):
        self._inverted = True
        return self

    def wrap(self):
        return validation_decorator(self)


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


class PigeonValidation(Validation[Pigeon], ABC):
    def get_target_type(self):
        return Pigeon

    def find_target(self, user_id: int) -> Optional[Pigeon]:
        from src.disc.commands import PigeonHelper
        return PigeonHelper().get_pigeon(user_id)


class HasPigeon(PigeonValidation):
    def _validate(self, target: Pigeon) -> bool:
        return target is not None

    def failure_message_self(self) -> str:
        return 'You do not have a pigeon.'

    def failure_message_other(self) -> str:
        return 'The other person does not have a pigeon.'


class HasStatus(PigeonValidation):
    def __init__(self, status: Pigeon.Status):
        super().__init__()
        self.status = status

    def _validate(self, target: Pigeon) -> bool:
        return target.status == self.status

    def failure_message_self(self) -> str:
        return 'Status bad'

    def failure_message_other(self) -> str:
        return 'Status bad'


def has_status(status: Pigeon.Status):
    return HasStatus(status).wrap()


def has_pigeon():
    return HasPigeon().wrap()


def does_not_have_pigeon():
    return HasPigeon().invert().wrap()


def has_gold(amount: int):
    return HasGold(amount).wrap()


def validation_decorator(validation: Validation):
    def wrapper(func):
        def inner(f):
            existing = f.extras.get('validations', [])
            existing.append(validation)
            f.extras['validations'] = existing
            return f

        return inner if func is None else inner(func)

    return wrapper
