from ..models import ConditionFlow, ConditionBlock, Condition
from .result import ValidationContext
from .conditions import IsValidator, ContainsValidator

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
            matched = validator.validate(context, condition)
            if matched is None:
                return False
            return int(matched) + int(condition.positive) != 1

        return False

    @classmethod
    def match_block(cls, context: ValidationContext, block: ConditionBlock) -> bool:
        for condition in block.conditions:
            if not cls.match_condition(context, condition):
                return False

        return True
