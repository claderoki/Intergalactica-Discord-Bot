from enum import Enum

from src.models.conversions import Currency, StoredUnit

class UnitType(Enum):
    measurement = 1
    currency    = 2

class UnitSubType(Enum):
    length      = 1
    temperature = 2
    mass        = 3

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
    __slots__ = ("unit", "value", "squared")

    def __init__(self, unit: Unit, value: float, squared: bool = False):
        self.unit    = unit
        self.value   = value
        self.squared = squared

    def __str__(self):
        if self.unit.type == UnitType.measurement:
            return f"{self.value}{self.unit.symbol}"
        else:
            return f"{self.value}{self.unit.code}"

    @classmethod
    def _normalize_value(cls, value) -> str:
        return str(int(value) if value % 1 == 0 else round(value, 2))

    def get_value_string(self):
        return self._normalize_value(self.value)

    def get_clean_string(self):
        if self.unit.type == UnitType.measurement:
            if self.squared:
                text = f"{self.get_value_string()}sq{self.unit.code}"
            else:
                text = f"{self.get_value_string()}{self.unit.symbol}"
                if self.unit.name == "feet" and not self.squared:
                    value = self.value
                    remaining = self.value % 1
                    value -= remaining
                    inches = self._normalize_value(remaining * 12)
                    text += f"\n{self._normalize_value(value)}'{inches}\""

            return text
        else:
            return f"{self.unit.symbol}{self.get_value_string()} ({self.unit.name})"

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