import re
from enum import Enum
from typing import Tuple, Set

import discord

from src.models import Human, Currency, Measurement
from src.models.conversions import ServerCurrency
from .models import StoredUnit, UnitType


class RegexType(Enum):
    currency = 1
    measurement = 2


class CurrencyCache:
    symbols_with_duplicates = []


class RegexHelper:
    __slots__ = ("type", "values", "_regex", 'abbreviation_check', '_built_with_no_values')

    def __init__(self, type: RegexType, abbreviation_check: bool = False):
        self.type = type
        self.values = set()
        self.abbreviation_check = abbreviation_check
        self._regex = None
        self._built_with_no_values = True

    def add_value(self, value):
        if self.values is None:
            self.values = set()
            self._regex = None
        self.values.add(value)

    def rebuild(self, raw: str):
        self._regex = self._build()

    def _build(self, raw: str = None):
        if self.type == RegexType.currency:
            format = "({values})(\d+(\.\d+)*)(?!\w)"
        elif self.type == RegexType.measurement:
            format = "([+-]?\d+(\.\d+)*)({values})(?!\w)"
        regex = format.format(values="|".join([x.replace('$', '\\$') for x in self.values]))
        # self.values = None
        return re.compile(regex)

    @property
    def regex(self):
        if self._regex is None or self._built_with_no_values:
            if len(self.values) == 0:
                self._built_with_no_values = True
            self._regex = self._build()
        return self._regex

    def _index_or_none(self, content, index):
        if index < 0:
            return None
        try:
            return content[index]
        except IndexError:
            return None

    _NUMERICAL_ABBREVIATIONS = ('k', 'm')

    def _get_abbreviation(self, after_end: str):
        if after_end in self._NUMERICAL_ABBREVIATIONS:
            return after_end

    def match(self, content) -> Tuple[str, float]:
        i = 0
        for match in re.finditer(self.regex, content):
            char_after_end = self._index_or_none(content, match.end()) or ' '
            char_before_start = self._index_or_none(content, match.start() - 1) or ' '
            allowed = (' ', '°')

            end_valid = char_after_end in allowed
            start_valid = char_before_start in allowed

            abbreviation = None
            if self.abbreviation_check:
                abbreviation = self._get_abbreviation(char_after_end)
                if abbreviation:
                    end_valid = True

            if not end_valid or not start_valid:
                continue

            groups = [x for x in match.regs if x not in ((-1, -1), (match.start(), match.end()))]
            match = [content[x[0]:x[1]] for x in groups]

            if self.type == RegexType.measurement:
                value = float(match[0])
                unit = match[-1]
            elif self.type == RegexType.currency:
                unit = match[0]
                value = float(match[1])

            if abbreviation == 'k':
                value = value * 1000
            elif abbreviation == 'm':
                value = value * 1000000
            if unit is not None and value is not None:
                yield unit, value
            i += 1


class UnitMapping:
    __slots__ = ("values",)

    def __init__(self):
        self.values = {}

    def __iter__(self):
        yield from self.values

    def clear(self):
        self.values.clear()

    def _add_value(self, value: str, stored_unit: StoredUnit):
        value = value.lower()
        if value in self.values:
            existing = self.values[value]
            if existing == stored_unit:
                return

            if isinstance(existing, list) and stored_unit not in existing:
                existing.append(stored_unit)
            else:
                self.values[value] = [existing, stored_unit]
        else:
            self.values[value] = stored_unit

    def get_unit(self, value, type: UnitType = None):
        units = self.get_units(value, type=type)
        if units is not None and len(units) > 0:
            return units[0]

    def get_units(self, value, type: UnitType = None, filter=None):
        try:
            unit = self.values[value.lower()]
        except KeyError as e:
            return []
        if filter is None:
            filter = lambda x: True

        all_units = []
        if isinstance(unit, list):
            all_units.extend(unit)
        else:
            all_units.append(unit)
        all_units = [x for x in all_units if filter(x)]

        if type is None:
            return all_units

        units = []
        if type is not None:
            for unit in all_units:
                if type == UnitType.measurement and isinstance(unit, Measurement):
                    units.append(unit)
                elif type == UnitType.currency and isinstance(unit, Currency):
                    units.append(unit)
        return units

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


class CurrencyContext:
    def __init__(self):
        self.data = {}


async def fetch_context_currency_codes(message) -> Set[str]:
    query = Human.select(Human.country, Human.currencies)
    query = query.where((Human.country != None) | (Human.currencies.is_null(False)))

    currencies = set()

    ids = {message.author.id}
    if not isinstance(message.channel, discord.DMChannel) and message.guild is not None:
        serverwide = (Currency.select(Currency.code)
                      .where(ServerCurrency.guild_id == message.guild.id)
                      .join(ServerCurrency))
        for server_currency in serverwide:
            currencies.add(server_currency.code)

        async for msg in message.channel.history(limit=20):
            if not msg.author.bot:
                ids.add(msg.author.id)

    query = query.where(Human.user_id.in_(ids))

    for human in query:
        for currency in human.all_currencies:
            if currency is not None:
                currencies.add(currency.alpha_3)

    return currencies


def test():
    pass

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
