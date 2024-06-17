from abc import ABC
from typing import Optional

from src.disc.commands.base.validation import Validation, Invertable
from src.models import Pigeon


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
        return f'Your pigeon needs to be {self.status.get_verb()} to perform this action.'

    def failure_message_other(self) -> str:
        return f'The other persons pigeon needs to be {self.status.get_verb()} to perform this action.'


class HasStatusInList(PigeonValidation):
    def __init__(self, *statuses: Pigeon.Status):
        super().__init__()
        self.statuses = statuses

    def _validate(self, target: Pigeon) -> bool:
        return target.status in self.statuses

    def _format(self):
        return ' | '.join([x.get_verb() for x in self.statuses])

    def failure_message_self(self) -> str:
        return f'Your pigeon needs to be {self._format()} to perform this action.'

    def failure_message_other(self) -> str:
        return f'The other persons pigeon needs to be {self._format()} to perform this action.'


class StatLessThan(PigeonValidation):
    def __init__(self, name: str, value: int, self_override: str = None):
        super().__init__()
        self.name = name
        self.value = value
        self.failure_message_self_override = self_override

    def _validate(self, target: Pigeon) -> bool:
        value = getattr(target, self.name)
        return value < self.value

    def failure_message_self(self) -> str:
        return f'Your pigeon needs to have under {self.value} {self.name} for this action'

    def failure_message_other(self) -> str:
        return f'The other persons pigeon needs to have under {self.value} {self.name} for this action'


def food_less_than(value: int, override: str = None):
    return StatLessThan('food', value, override).wrap()


def cleanliness_less_than(value: int, override: str = None):
    return StatLessThan('cleanliness', value, override).wrap()


def health_less_than(value: int, override: str = None):
    return StatLessThan('health', value, override).wrap()


def happiness_less_than(value: int, override: str = None):
    return StatLessThan('happiness', value, override).wrap()


def has_status(status: Pigeon.Status):
    return HasStatus(status).wrap()


def status_in(*statuses: Pigeon.Status):
    return HasStatus(status).wrap()


def has_pigeon():
    return HasPigeon().wrap()


def does_not_have_pigeon():
    return HasPigeon().invert().wrap()
