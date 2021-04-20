import re
from enum import Enum

import discord

from .models import StoredUnit
from src.models import Human

class RegexType(Enum):
    currency   = 1
    measurement = 2

class RegexHelper:
    __slots__ = ("type", "values", "_regex")

    def __init__(self, type: RegexType):
        self.type   = type
        self.values = set()
        self._regex = None

    def add_value(self, value):
        self.values.add(value)

    def _build(self):
        if self.type == RegexType.currency:
            format = "({values})(\d+(\.\d+)*)(?!\w)"
        elif self.type == RegexType.measurement:
            format = "([+-]?\d+(\.\d+)*)({values})(?!\w)"
        regex = format.format(values = "|".join(self.values))
        self.values = None
        return regex

    @property
    def regex(self):
        if self._regex is None:
            self._regex = self._build()
        return self._regex

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
                yield unit, value

class UnitMapping:
    __slots__ = ("values")

    def __init__(self):
        self.values = {}

    def __iter__(self):
        yield from self.values

    def _add_value(self, value: str, stored_unit: StoredUnit):
        value = value.lower()
        if value in self.values:
            existing = self.values[value]
            if existing == stored_unit:
                return

            if isinstance(existing, list):
                existing.append(stored_unit)
            else:
                self.values[value] = [existing, stored_unit]
        else:
            self.values[value] = stored_unit

    def get_unit(self, value):
        units = self.get_units(value)
        if units is not None:
            return units[0]

    def get_units(self, value):
        try:
            unit = self.values[value.lower()]
        except KeyError:
            return None
        if not isinstance(unit, list):
            unit = [unit]
        return unit

    def add(self, stored_unit: StoredUnit):
        symbol = stored_unit.symbol.lower()
        if not stored_unit.should_exclude_symbol:
            self._add_value(symbol, stored_unit)
        self._add_value(stored_unit.code.lower(), stored_unit)

def get_other_measurements():
    measurements = (
        ("c", "f"),
        ("kg", "lb"),
        ("g", "oz"),
        ("cm", "inch", "ft"),
        ("ml", "us_cup"),
        ("km", "mi"),
        ("m", "yd", "ft"),
    )

    other_measurements = {}
    for equivalents in measurements:
        for unit in equivalents:
            for other_unit in equivalents:
                if other_unit != unit:
                    if unit not in other_measurements:
                        other_measurements[unit] = [other_unit]
                    else:
                        other_measurements[unit].append(other_unit)
    return other_measurements

async def get_context_currency_codes(message):
    query = Human.select(Human.country, Human.currencies)
    query = query.where((Human.country != None) | (Human.currencies != None))

    ids = set((message.author.id, ))
    if not isinstance(message.channel, discord.DMChannel):
        if message.guild is not None:
            async for msg in message.channel.history(limit=20):
                if not msg.author.bot:
                    ids.add(msg.author.id)

    query = query.where(Human.user_id.in_(ids))

    currencies = set()
    for human in query:
        for currency in human.all_currencies:
            if currency is not None:
                currencies.add(currency.alpha_3)

    return currencies

def should_exclude(value):
    return "." in value or "$" in value

# from measurement.measures import Mass

# def first_save(type):
#     base_unit = type.STANDARD_UNIT
#     base = type(**{type.STANDARD_UNIT: 1})
#     subtype = UnitSubType[type.__name__.lower()]

#     for unit in type.get_units():
#         value = getattr(base, unit)
#         measurement = Measurement(
#             rate = value,
#             name = unit,
#             is_base = unit == base_unit,
#             code = unit,
#             symbol = unit,
#             subtype = subtype
#         )
#         # measurement.save()
