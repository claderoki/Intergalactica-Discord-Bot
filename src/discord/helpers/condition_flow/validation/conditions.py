import re

import discord

from .result import ValidationContext
from ..models import MessageCondition, UserCondition, MemberCondition, Condition


class ConditionValidator:
    __slots__ = ()

    def __init_subclass__(cls) -> None:
        for method in ("_validate_member", "_validate_user", "_validate_message"):
            if not hasattr(cls, method):
                raise Exception(f"Method {method} is not implemented")

    @classmethod
    def validate(cls, context: ValidationContext, condition: Condition) -> bool:
        if isinstance(condition, MessageCondition):
            if not hasattr(context, "message") or not isinstance(context.message, (discord.Message)):
                return False
            return cls._validate_message(context.user, condition)
        if isinstance(condition, MemberCondition):
            if not hasattr(context, "member") or not isinstance(context.member, discord.Member):
                return False
            return cls._validate_member(context.member, condition)
        if isinstance(condition, UserCondition):
            if not hasattr(context, "user") or not isinstance(context.user, (discord.User, discord.Member)):
                return False
            return cls._validate_user(context.user, condition)


class ContainsValidator(ConditionValidator):
    __slots__ = ()

    @classmethod
    def _validate_message(cls, message: discord.User, condition: MessageCondition) -> bool:
        pass

    @classmethod
    def _validate_user(cls, user: discord.User, condition: UserCondition) -> bool:
        pass

    @classmethod
    def _validate_member(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.source == MemberCondition.Source.role:
            for role in member.roles:
                if role.id in condition.value.values:
                    return True
            return False


class IsValidator(ConditionValidator):
    __slots__ = ()

    @classmethod
    def _validate_message(cls, message: discord.User, condition: MessageCondition) -> bool:
        pass

    @classmethod
    def _validate_user(cls, user: discord.User, condition: UserCondition) -> bool:
        if condition.source == UserCondition.Source.bot:
            return user.bot

    @classmethod
    def _validate_member(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.source == MemberCondition.Source.nitro_booster:
            return member.premium_since is not None


class RegexValidator(ConditionValidator):
    __slots__ = ()

    @classmethod
    def _validate_user(cls, user: discord.User, condition: UserCondition) -> bool:
        pass

    @classmethod
    def _validate_member(cls, member: discord.Member, condition: MemberCondition) -> bool:
        pass

    @classmethod
    def _validate_message(cls, message: discord.Message, condition: MessageCondition) -> bool:
        if condition.source == MessageCondition.Source.content:
            regex = re.compile(condition.value)
            matches = regex.findall(message.content)
            return len(matches) > 0
