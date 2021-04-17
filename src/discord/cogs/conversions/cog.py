import re

import discord
from discord.ext import tasks, commands
from discord.shard import EventItem

import src.config as config
from src.models import Human, Earthling, Currency, Measurement, StoredUnit, database
from src.discord.cogs.core import BaseCog
from src.wrappers.fixerio import Api as FixerioApi
from .models import Unit, UnitSubType, UnitType, Conversion, ConversionResult
from .helper import RegexHelper, RegexType


measurements = [
    ("c", "f"),
    ("kg", "lb"),
    ("g", "oz"),
    ("cm", "inch", "ft"),
    ("ml", "us_cup"),
    ("km", "mi"),
    ("m", "yd", "ft"),
]

other_measurements = {}

for equivalents in measurements:
    for unit in equivalents:
        for other_unit in equivalents:
            if other_unit != unit:
                if unit not in other_measurements:
                    other_measurements[unit] = [other_unit]
                else:
                    other_measurements[unit].append(other_unit)

unit_mapping = {}
currency_units = set()
measurement_units = set()

measurement_regex = RegexHelper(RegexType.measurement)

def add_to_mapping(text, stored_unit: StoredUnit, is_symbol):
    text = text.lower()
    if text in unit_mapping:
        existing = unit_mapping[text]

        if not is_symbol and existing != stored_unit:
            print(value, "is double =>", existing, stored_unit, ", skipping.")
            return
        if isinstance(existing, list):
            existing.append(stored_unit)
        else:
            unit_mapping[text] = [existing, stored_unit]
    else:
        unit_mapping[text] = stored_unit

    if isinstance(stored_unit, Currency):
        measurement_regex.add_value(text)
    elif isinstance(stored_unit, Measurement):
        measurement_regex.add_value(text)

    return unit_mapping[text]

for cls in (Currency, Measurement):
    for stored_unit in cls:
        for value in (stored_unit.code, stored_unit.symbol):
            is_symbol = value == stored_unit.symbol and value != stored_unit.code

            value = value.lower()
            if (cls == Currency and not is_symbol) or cls == Measurement:
                add_to_mapping(value, stored_unit, is_symbol)

            if "." not in value and "$" not in value:
                array = currency_units if cls == Currency else measurement_units
                array.add(value)

def get_context_currency_codes(message):
    return ["PHP", "USD"]

def get_linked_codes(base: Conversion, message: discord.Message):
    if base.unit.type == UnitType.measurement:
        return other_measurements[base.unit.code]
    else:
        return get_context_currency_codes(message)

def convert(base: StoredUnit, to: StoredUnit, value: float) -> float:
    if base.code == "c" and to.code == "f":
        return (value * 1.8) + 32
    elif base.code == "f" and to.code == "c":
        return (value - 32) / 1.8
    else:
        return (to.rate * value) / base.rate

def base_to_conversion_result(base_stored_unit: StoredUnit, value: float, message: discord.Message) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value)
    to   = []
    for code in get_linked_codes(base, message):
        code = code.lower()
        stored_unit = unit_mapping[code]
        converted   = convert(base_stored_unit, stored_unit, value)
        to.append(Conversion(Unit.from_stored_unit(stored_unit), converted))
    return ConversionResult(base, to)

def text_to_units(text):
    try:
        unit = unit_mapping[text.lower()]
    except KeyError:
        return None
    if not isinstance(unit, list):
        unit = [unit]
    return unit

class ConversionCog(BaseCog, name = "Conversion"):
    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.currency_rate_updater, check = True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or "http" in message.content:
            return

        for unit, value in measurement_regex.match(message.content.lower()):
            pass
            conversion_results = []

            for match in matches:
                value = float(match[0])
                units = text_to_units(match[-1])
                for unit in units:
                    conversion_result = base_to_conversion_result(unit, value, message)
                    conversion_results.append(conversion_result)

            print(conversion_results)

    @tasks.loop(hours = 1)
    async def currency_rate_updater(self):
        api = FixerioApi(config.environ["fixerio_access_key"])
        pass

def setup(bot):
    bot.add_cog(ConversionCog(bot))


"""

    def _get_matches(self, content):
        cleaned_matches = []

        matches = re.findall(self.global_pattern, content)
        if matches:
            for match in matches:
                value = float(match[0])
                unit = match[-1]
                is_currency = unit.upper() in self.currency_converter.currencies or unit.lower() in currency_symbols.values()

                type = "currency" if is_currency else "measurement"

                aliases_found = False
                for _unit, alias in units.items():
                    if alias.lower() == unit:
                        aliases_found = True
                        cleaned_matches.append({"value" : value, "unit" : _unit, "type": type})
                if not aliases_found:
                    cleaned_matches.append({"value" : value, "unit" : unit, "type": type})

        matches = re.findall(self.currency_pattern, content)
        if matches:
            for match in matches:
                symbol = match[0]
                value = match[1]
                for alpha_2, _symbol in currency_symbols.items():
                    if symbol == _symbol:
                        cleaned_matches.append({"value" : value, "unit" : alpha_2.lower(), "type": "currency"})

        matches = re.findall(self.timezone_pattern, content)
        if matches:
            for match in matches:
                timezone, symbol, amount = match
                symbol = symbol or "+"
                amount = amount or "0"
                amount = int(amount)
                value = amount if symbol != "-" else -amount
                cleaned_matches.append({"value" : value, "unit" : timezone, "type": "timezone"})

        return cleaned_matches

"""