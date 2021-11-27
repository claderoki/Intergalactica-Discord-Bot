
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
        contains = "contains"
        is_       = "is"

    class Source:
        pass

    __slots__ = ("source", "value", "type", "positive")

    def __init__(self, source: Source, type: Type, value: ConditionValue, positive: bool = True):
        self.source = source
        self.type = type
        self.value = value
        self.positive = positive

    def reverse(self):
        self.positive = not self.positive

class UserCondition(Condition):
    class Type(Condition.Type):
        pass

    class Source(Condition.Source):
        bot = "bot"

    @classmethod
    def is_bot(cls) -> "UserCondition":
        return cls(
            source   = cls.Source.bot,
            type     = cls.Type.is_,
            value    = None,
        )

class MemberCondition(UserCondition):
    class Type(UserCondition.Type):
        pass

    class Source(UserCondition.Source):
        role          = "role"
        nitro_booster = "nitro_booster"

    @classmethod
    def has_any_role(cls, *role_ids) -> "MemberCondition":
        return cls(
            source   = cls.Source.role,
            type     = cls.Type.contains,
            value    = ConditionMultipleValue(role_ids),
        )

    @classmethod
    def is_nitro_booster(cls) -> "MemberCondition":
        return cls(
            source   = cls.Source.nitro_booster,
            type     = cls.Type.is_,
            value    = None,
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
