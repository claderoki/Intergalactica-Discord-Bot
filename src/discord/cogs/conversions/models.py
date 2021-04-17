from enum import Enum

from src.models.conversions import Currency, Measurement, StoredUnit

class UnitType(Enum):
    measurement = 1
    currency    = 2

class UnitSubType(Enum):
    length      = 1
    temperature = 2

class Unit:
    __slots__ = ("name", "code", "symbol", "type", "subtype")

    def __init__(self, name, code, symbol, type: UnitType, subtype: UnitSubType):
        self.name    = name
        self.code    = code
        self.symbol  = symbol
        self.type    = type
        self.subtype = subtype

    @classmethod
    def from_stored_unit(cls, stored_unit: StoredUnit):
        if isinstance(stored_unit, Currency):
            return cls(stored_unit.name, stored_unit.code, stored_unit.symbol, UnitType.currency, None)
        else:
            return cls(stored_unit.name, stored_unit.code, stored_unit.symbol, UnitType.measurement, stored_unit.subtype)

class Conversion:
    __slots__ = ("unit", "value")

    def __init__(self, unit: Unit, value: float):
        self.unit = unit
        self.value = value

    def __str__(self):
        return f"{self.value}{self.unit.symbol}"

class ConversionResult:
    __slots__ = ("base", "to")

    def __init__(self, base: Conversion, to: list):
        self.base = base
        self.to   = to

    def __repr__(self):
        return str(self)

    def __str__(self):
        values = []
        values.append(str(self.base))
        for to in self.to:
            values.append(str(to))
        return "\n".join(values)