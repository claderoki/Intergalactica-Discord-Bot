
class ConditionValue:
    __slots__ = ()

class ConditionSingleValue:
    __slots__ = ("value", )

    def __init__(self, value):
        self.value = value

class ConditionMultipleValue(ConditionValue):
    __slots__ = ("values", )

    def __init__(self, values):
        self.values = values

class Condition:
    class Type:
        contains = 1

    class Source:
        pass

    __slots__ = ("source", "value", "type", "positive")

    def __init__(self, source: Source, type: Type, value: ConditionValue, positive: bool = True):
        self.source = source
        self.type = type
        self.value = value
        self.positive = positive

class MemberCondition(Condition):
    class Type(Condition.Type):
        pass

    class Source(Condition.Source):
        role = 1

    @classmethod
    def has_any_role(cls, *role_ids) -> "MemberCondition":
        return cls(
            source = cls.Source.role,
            type   = cls.Type.contains,
            value  = ConditionMultipleValue(role_ids)
        )

class ConditionBlock:
    __slots__ = ("conditions", "position" )

    def __init__(self, conditions: list, position: int):
        self.conditions = conditions
        self.position   = position

    @classmethod
    def single(cls, condition: Condition, position: int):
        return cls([condition], position)

class ConditionFlow:
    __slots__ = ("blocks", )

    def __init__(self, blocks: list):
        self.blocks = blocks

# flow = ConditionFlow([
#     ConditionBlock.single(MemberCondition.has_any_role(778744417322139689), 0),
#     ConditionBlock.single(MemberCondition.has_any_role(778744417322139689), 1)
# ])
