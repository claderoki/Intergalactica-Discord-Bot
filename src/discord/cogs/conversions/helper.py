import re
from enum import Enum

class RegexType(Enum):
    currency   = 1
    measurement = 2

class RegexHelper:
    __slots__ = ("type", "values")

    def __init__(self, type: RegexType):
        self.type   = type
        self.values = set()
        self.regex  = None

    def add_value(self, value):
        self.values.add(value)

    def _build(self):
        if self.type == RegexType.currency:
            format = "({})(\d+(\.\d+)*)(?!\w)"
        elif self.type == RegexType.measurement:
            format = "([+-]?\d+(\.\d+)*)({values})(?!\w)"
        return format.format(values = "|".join(self.values))

    @property
    def regex(self):
        if self.regex is None:
            self.regex = self._build()
        return self.regex

    def match(self, content):
        matches = re.findall(self.regex, content)
        if matches:
            for match in matches:
                if self.type == RegexType.measurement:
                    value = float(match[0])
                    unit = match[-1]
                elif self.type == RegexType.currency:
                    unit = match[0]
                    value = float(match[1])

                yield value, unit