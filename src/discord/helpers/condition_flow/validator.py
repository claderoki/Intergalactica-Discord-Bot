import discord

from .models import ConditionFlow, MemberCondition, ConditionBlock, ConditionValue

class ConditionFlowValidator:
    __slots__ = ()

    @classmethod
    def match_flow(cls, member: discord.Member, flow: ConditionFlow) -> bool:
        for block in flow.blocks:
            if cls.match_block(member, block):
                return True

        return False

    @classmethod
    def _member_contains(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.source == MemberCondition.Source.role:
            for role in member.roles:
                contains = role.id in condition.value.values
                if contains:
                    return condition.positive
        return not condition.positive

    @classmethod
    def match_condition(cls, member: discord.Member, condition: MemberCondition) -> bool:
        if condition.type == MemberCondition.Type.contains:
            return cls._member_contains(member, condition)

    @classmethod
    def match_block(cls, member: discord.Member, block: ConditionBlock) -> bool:
        for condition in block.conditions:
            if not cls.match_condition(member, condition):
                return False

        return True

