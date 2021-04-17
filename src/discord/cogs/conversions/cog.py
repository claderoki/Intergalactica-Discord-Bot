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


from measurement.measures import Mass

# base = Mass(g = 1)

# for unit in Mass.get_units():
#     value = getattr(base, unit)
#     measurement = Measurement(
#         rate = value,
#         name = unit,
#         is_base = unit == "g",
#         code = unit,
#         symbol = unit,
#         subtype = UnitSubType.mass
#     )
#     measurement.save()

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
        if existing == stored_unit:
            return

        if not is_symbol:
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

async def get_context_currency_codes(message):
    query = Human.select(Human.country, Human.currencies)
    query = query.join(Earthling, on=(Human.id == Earthling.human))
    query = query.where((Human.country != None) | (Human.currencies != None))

    ids = set((message.author.id, ))
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

async def get_linked_codes(base: Conversion, message: discord.Message):
    if base.unit.type == UnitType.measurement:
        try:
            return other_measurements[base.unit.code]
        except KeyError:
            return []
    else:
        return await get_context_currency_codes(message)

def convert(base: StoredUnit, to: StoredUnit, value: float) -> float:
    if base.code == "c" and to.code == "f":
        return (value * 1.8) + 32
    elif base.code == "f" and to.code == "c":
        return (value - 32) / 1.8
    else:
        return (to.rate * value) / base.rate

async def base_to_conversion_result(base_stored_unit: StoredUnit, value: float, message: discord.Message) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value)
    to   = []
    for code in await get_linked_codes(base, message):
        code = code.lower()
        if code == base_stored_unit.code.lower():
            continue
        try:
            stored_unit = unit_mapping[code]
        except KeyError:
            continue

        if isinstance(stored_unit, list):
            print(stored_unit, "wtf?")
            continue

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

def add_conversion_result_to_embed(embed: discord.Embed, conversion_result: ConversionResult):
    kwargs = {}
    kwargs["name"] = conversion_result.base.get_clean_string()
    lines = []
    for to in conversion_result.to:
        lines.append(to.get_clean_string())
    if len(lines) == 0:
        return

    kwargs["value"] = "\n".join(lines)
    embed.add_field(**kwargs)

class ConversionCog(BaseCog, name = "Conversion"):
    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.currency_rate_updater, check = self.bot.production)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or "http" in message.content:
            return

        conversion_results = []
        for unit_value, value in measurement_regex.match(message.content.lower()):
            units = text_to_units(unit_value)
            for unit in units:
                conversion_result = await base_to_conversion_result(unit, value, message)
                conversion_results.append(conversion_result)

        embed = discord.Embed(color = self.bot.get_dominant_color())
        if len(conversion_results) > 0:
            for result in conversion_results:
                add_conversion_result_to_embed(embed, result)
        if len(embed.fields) > 0:
            await message.channel.send(embed = embed)

    @tasks.loop(hours = 1)
    async def currency_rate_updater(self):
        api = FixerioApi(config.environ["fixerio_access_key"])
        rates = api.latest()["rates"]
        for alpha_3, rate in rates.items():
            if alpha_3.lower() in unit_mapping:
                currency = unit_mapping[alpha_3.lower()]
                if isinstance(currency, Currency):
                    currency.rate = rate
                    currency.save()

def setup(bot):
    bot.add_cog(ConversionCog(bot))