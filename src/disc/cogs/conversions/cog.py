import discord
import pycountry
from discord import app_commands
from discord.ext import tasks, commands

from src.config import config
from src.disc.cogs.core import BaseCog
from src.models import Currency, Measurement, StoredUnit, Human
from src.wrappers.fixerio import Api as FixerioApi
from .helper import RegexHelper, RegexType, UnitMapping, get_other_measurements, fetch_context_currency_codes
from .models import Unit, UnitType, Conversion, ConversionResult
from ...commands import BaseGroupCog

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
    elif isinstance(stored_unit, Measurement) and stored_unit.squareable:
        measurement_regex.add_value(f"sq{stored_unit.code.lower()}")


def add_all_to_mapping():
    for cls in (Currency, Measurement):
        for stored_unit in cls:
            unit_mapping.add(stored_unit)
            add_stored_unit_to_regexes(stored_unit)


add_all_to_mapping()


def base_measurement_to_conversion_result(base_stored_unit: StoredUnit, value: float) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value)
    to = []
    for code in get_linked_measurements(base):
        code = code.lower()
        if code == base_stored_unit.code.lower():
            continue
        stored_unit = unit_mapping.get_unit(code, type=base.unit.type)

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


async def get_linked_codes(base: Conversion, message: discord.Message, cache: dict):
    if base.unit.type == UnitType.measurement:
        return get_linked_measurements(base)
    else:
        if message.id not in cache:
            cache[message.id] = await fetch_context_currency_codes(message)
        return cache[message.id]


async def base_to_conversion_result(base_stored_unit: StoredUnit, value: float, message: discord.Message,
                                    squared: bool = False) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value, squared=squared)
    to = []
    _context_cache = {}
    for code in await get_linked_codes(base, message, _context_cache):
        code = code.lower()
        if code == base_stored_unit.code.lower():
            continue
        stored_unit = unit_mapping.get_unit(code, type=base.unit.type)

        if stored_unit is None:
            continue

        if squared and isinstance(stored_unit, Measurement) and not stored_unit.squareable:
            continue

        converted = base_stored_unit.to(stored_unit, value, squared)
        to.append(Conversion(Unit.from_stored_unit(stored_unit), converted, squared=squared))
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


class ConversionCog(BaseGroupCog, name="currency"):
    unit_mapping = unit_mapping

    @classmethod
    def base_measurement_to_conversion_result(cls, base_stored_unit: StoredUnit, value: float) -> ConversionResult:
        return base_measurement_to_conversion_result(base_stored_unit=base_stored_unit, value=value)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.currency_rate_updater, check=self.bot.production)

    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name='add', description='add a currency you\'d like to enable converting.')
    async def currency_add(self, interaction: discord.Interaction, currency_code: str):
        currency = pycountry.currencies.get(alpha_3=currency_code.upper())
        if not currency:
            await interaction.response.send_message('This currency does not exist.')
            return

        human = self.bot.get_human(user=interaction.user)
        before = len(human.currencies)
        human.currencies.add(currency)
        if len(human.currencies) == before:
            await interaction.response.send_message('This currency is already added')
            return
        human.save(only=[Human.currencies])
        flattened = ", ".join(set(x.alpha_3 for x in human.currencies if x is not None))
        await interaction.response.send_message('This currency has been added, current currencies = ' + flattened)

    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name='remove')
    async def currency_remove(self, interaction: discord.Interaction, currency_code: str):
        human = self.bot.get_human(user=interaction.user)
        currency = pycountry.currencies.get(alpha_3=currency_code.upper())
        if currency in human.currencies:
            human.currencies.remove(currency)
            human.save(only=[Human.currencies])
            flattened = ", ".join(set(x.alpha_3 for x in human.currencies if x is not None))
            await interaction.response.send_message('This currency has been removed, current currencies = ' + flattened)
        else:
            await interaction.response.send_message('This currency isn\'t set for you.')

        human.currencies.remove(currency_code)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return

        if message.author.bot or "http" in message.content:
            return

        conversion_results = []
        for regex in (measurement_regex, currency_regex):
            for unit_value, value in regex.match(message.content.lower()):
                squared = False
                if "sq" in unit_value:
                    unit_value = unit_value.replace("sq", "")
                    squared = True

                units = unit_mapping.get_units(unit_value)
                for unit in units:
                    conversion_result = await base_to_conversion_result(unit, value, message, squared=squared)
                    conversion_results.append(conversion_result)

        embed = discord.Embed(color=self.bot.get_dominant_color())
        if len(conversion_results) > 0:
            for result in conversion_results:
                add_conversion_result_to_embed(embed, result)
        if len(embed.fields) > 0:
            await message.channel.send(embed=embed)

    @tasks.loop(hours=8)
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


async def setup(bot):
    await bot.add_cog(ConversionCog(bot))
