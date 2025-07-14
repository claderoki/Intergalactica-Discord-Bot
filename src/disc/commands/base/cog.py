from typing import List

import discord
import peewee
from discord.app_commands import CommandInvokeError
from discord.ext import commands

from src.disc.commands.base.validation import Validation
from src.models import Human, Pigeon


class CheckResult:
    def __init__(self, targets: 'TargetCollection', errors: List[str]):
        self.targets = targets
        self.errors = errors


class TargetCollection(dict):
    def __init__(self):
        super().__init__()

    def get_human(self) -> Human:
        return self.get(Human)

    def get_pigeon(self) -> Pigeon:
        return self.get(Pigeon)


class ValidationFailed(Exception):
    pass


class BaseGroupCog(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot

    def check(self,
              user_id: int,
              other: bool = False,
              validations: List[Validation] = None
              ) -> CheckResult:
        validations = validations or []
        targets = TargetCollection()
        errors = []
        for validation in validations:
            type = validation.get_target_type()
            if type not in targets:
                targets[type] = validation.find_target(user_id)
            if not validation.validate(targets[type]):
                errors.append(validation.get_message(other=other))
                return CheckResult(targets, errors)

        return CheckResult(targets, errors)

    @staticmethod
    def start_task(task, check: callable = lambda: True):
        if callable(check):
            check = check()

        if check:
            task.add_exception_type(peewee.OperationalError)
            task.add_exception_type(peewee.InterfaceError)
            try:
                task.start()
            except RuntimeError:
                pass

    def probability(self, interaction: discord.Interaction):
        return interaction.command.extras['probabilities'].choice()

    async def validate(self,
                       interaction: discord.Interaction,
                       user_id: int = None,
                       other: bool = False,
                       validations: List[Validation] = None
                       ) -> TargetCollection:
        validations = validations or interaction.command.extras.get('validations')
        result = self.check(user_id=user_id or interaction.user.id, other=other, validations=validations)
        if result.errors:
            await interaction.response.send_message(result.errors[0])
            raise ValidationFailed()
        return result.targets

    async def cog_app_command_error(self, interation, error):
        original = error.original if isinstance(error, CommandInvokeError) else error
        if not isinstance(original, ValidationFailed):
            raise error
