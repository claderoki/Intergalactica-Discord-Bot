import re

import discord
from discord.ext import tasks, commands
from discord.shard import EventItem

import src.config as config
from src.models import Human, Earthling, Currency, Measurement, StoredUnit, database
from src.discord.cogs.core import BaseCog
from src.wrappers.fixerio import Api as FixerioApi
from .models import Unit, UnitSubType, UnitType, Conversion, ConversionResult
from .helper import RegexHelper, RegexType, UnitMapping, should_exclude, get_other_measurements, get_context_currency_codes

other_measurements = get_other_measurements()
unit_mapping = UnitMapping()
measurement_regex = RegexHelper(RegexType.measurement)
currency_regex = RegexHelper(RegexType.currency)

def add_stored_unit_to_regexes(stored_unit: StoredUnit):
    measurement_regex.add_value(stored_unit.code.lower())
    if isinstance(stored_unit, Currency):
        symbol = stored_unit.symbol.lower()
        if not stored_unit.should_exclude_symbol:
            currency_regex.add_value(symbol)

def add_all_to_mapping():
    for cls in (Currency, Measurement):
        for stored_unit in cls:
            unit_mapping.add(stored_unit)
            add_stored_unit_to_regexes(stored_unit)

add_all_to_mapping()

def base_measurement_to_conversion_result(base_stored_unit: StoredUnit, value: float) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value)
    to   = []
    for code in get_linked_measurements(base):
        code = code.lower()
        if code == base_stored_unit.code.lower():
            continue
        stored_unit = unit_mapping.get_unit(code, type = base.unit.type)

        if stored_unit is None:
            continue

        converted = base_stored_unit.to(stored_unit, value)
        to.append(Conversion(Unit.from_stored_unit(stored_unit), converted))
    return ConversionResult(base, to)

def get_linked_measurements(base: Conversion):
    try:
        return other_measurements[base.unit.code]
    except KeyError:
        return ()

async def get_linked_codes(base: Conversion, message: discord.Message):
    if base.unit.type == UnitType.measurement:
        return get_linked_measurements(base)
    else:
        return await get_context_currency_codes(message)

async def base_to_conversion_result(base_stored_unit: StoredUnit, value: float, message: discord.Message) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value)
    to   = []
    for code in await get_linked_codes(base, message):
        code = code.lower()
        if code == base_stored_unit.code.lower():
            continue
        stored_unit = unit_mapping.get_unit(code, type = base.unit.type)

        if stored_unit is None:
            continue

        converted = base_stored_unit.to(stored_unit, value)
        to.append(Conversion(Unit.from_stored_unit(stored_unit), converted))
    return ConversionResult(base, to)

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
    unit_mapping = unit_mapping

    @classmethod
    def base_measurement_to_conversion_result(cls, base_stored_unit: StoredUnit, value: float) -> ConversionResult:
        return base_measurement_to_conversion_result(base_stored_unit = base_stored_unit, value = value)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.currency_rate_updater, check = self.bot.production)

    @commands.command()
    async def conversions(self, ctx):
        embed = discord.Embed(color = self.bot.get_dominant_color())
        # embed.add_field(
        #     name = "Measurements",
        #     value = "EXPLANATION",
        #     inline = False
        # )
        embed.add_field(
            name = "Currencies",
            value = """Currencies can be converted the following ways:
by writing either **€50** or **50EUR** in the chat.
(*note: some symbols that are used for too many currencies are excluded, like the dollar symbol*)

Whatever you write in chat will be converted to currencies based on the conversation:
All the users that wrote something for the last 20 messages are collected and their currencies are used to convert to.
(note: you will have to have a country set `/profile setup country` or have some currencies added `currency add usd`)
""",
            inline = False
        )
        await ctx.send(embed = embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return

        if message.author.bot or "http" in message.content:
            return

        conversion_results = []
        for regex in (measurement_regex, currency_regex):
            for unit_value, value in regex.match(message.content.lower()):
                units = unit_mapping.get_units(unit_value)
                for unit in units:
                    conversion_result = await base_to_conversion_result(unit, value, message)
                    conversion_results.append(conversion_result)

        embed = discord.Embed(color = self.bot.get_dominant_color())
        if len(conversion_results) > 0:
            for result in conversion_results:
                add_conversion_result_to_embed(embed, result)
        if len(embed.fields) > 0:
            await message.channel.send(embed = embed)

    @tasks.loop(hours = 8)
    async def currency_rate_updater(self):
        api = FixerioApi(config.environ["fixerio_access_key"])
        rates = api.latest()["rates"]
        values = unit_mapping.values
        for alpha_3, rate in rates.items():
            if alpha_3.lower() in values:
                currency = values[alpha_3.lower()]
                if isinstance(currency, Currency):
                    currency.rate = rate
                    currency.save()

def setup(bot):
    bot.add_cog(ConversionCog(bot))