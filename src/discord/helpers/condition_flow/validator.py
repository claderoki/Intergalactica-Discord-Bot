import discord

from .models import ConditionFlow, MemberCondition, ConditionBlock, Condition

class ValidationContext:
    __slots__ = ("member", "user", "message", "channel", "guild")

    def __init__(self):
        pass

    @classmethod
    def from_message(cls, message: discord.Message):
        obj = cls()
        if isinstance(message.channel, discord.DMChannel):
            obj.user = message.author
        else:
            obj.member  = message.author
            obj.guild   = message.guild
            obj.message = message
        return obj

class ValidationError(Exception):
    pass

class ValidationResult:
    __slots__ = ("errors", )

    def __init__(self):
        self.errors = []

    def add_error(self, error):
        if isinstance(error, str):
            self.errors.append(ValidationError(error))
        else:
            self.errors.append(error)

class ConditionValidator:
    __slots__ = ()

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "_validate_member"):
            raise Exception("You don't have the _validate_member method")

    @classmethod
    def validate(cls, context: ValidationContext, condition: Condition) -> bool:
        if isinstance(condition, MemberCondition):
            if not hasattr(context, "member") or not isinstance(context.member, discord.Member):
                return False
            return cls._validate_member(context.member, condition)
        return False

class ContainsValidator(ConditionValidator):
    __slots__ = ()

    @classmethod
    def _validate_member(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.source == MemberCondition.Source.role:
            for role in member.roles:
                if role.id in condition.value.values:
                    return condition.positive
            return not condition.positive

        return False

class IsValidator(ConditionValidator):
    __slots__ = ()

    @classmethod
    def _validate_member(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.source == MemberCondition.Source.bot:
            return (int(condition.positive)+int(member.bot) != 1)
        elif condition.source == MemberCondition.Source.nitro_booster:
            return (int(member.premium_since is not None)+int(condition.positive) != 1)

condition_validation_mappings = {"is": IsValidator, "contains": ContainsValidator}

class ConditionFlowValidator:
    __slots__ = ()

    @classmethod
    def match_flow(cls, context: ValidationContext, flow: ConditionFlow) -> bool:
        for block in flow.blocks:
            if cls.match_block(context, block):
                return True

        return False

    @classmethod
    def match_condition(cls, context: ValidationContext, condition: Condition) -> bool:
        validator = condition_validation_mappings.get(condition.type)
        if validator is not None:
            return validator.validate(context, condition) == True

        return False

    @classmethod
    def match_block(cls, context: ValidationContext, block: ConditionBlock) -> bool:
        for condition in block.conditions:
            if not cls.match_condition(context, condition):
                return False

        return True
