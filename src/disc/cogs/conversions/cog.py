import typing

import discord
import peewee
import pycountry
from discord import app_commands
from discord.ext import tasks, commands

from src.config import config
from src.models import Currency, Measurement, StoredUnit, Human
from src.models.conversions import ServerCurrency
from src.wrappers.fixerio import Api as FixerioApi
from .helper import RegexHelper, RegexType, UnitMapping, get_other_measurements, fetch_context_currency_codes, CurrencyCache
from .models import Unit, UnitType, Conversion, ConversionResult
from ...commands import BaseGroupCog

other_measurements = get_other_measurements()
unit_mapping = UnitMapping()
measurement_regex = RegexHelper(RegexType.measurement)
currency_regex = RegexHelper(RegexType.currency)


def add_stored_unit_to_regexes(stored_unit: StoredUnit, add_to_currency: bool = True):
    measurement_regex.add_value(stored_unit.code.lower())
    if isinstance(stored_unit, Currency):
        if add_to_currency:
            currency_regex.add_value(stored_unit.symbol.lower())
    elif isinstance(stored_unit, Measurement) and stored_unit.squareable:
        measurement_regex.add_value(f"sq{stored_unit.code.lower()}")


def _load_duplicates(currencies):
    dupl = {}
    for c in currencies:
        dupl.setdefault(c.symbol.lower(), set()).add(c)
    CurrencyCache.symbols_with_duplicates = [k for k, v in dupl.items() if len(v) > 1]


def add_all_to_mapping():
    unit_mapping.clear()
    for measurement in Measurement:
        unit_mapping.add(measurement)
        add_stored_unit_to_regexes(measurement)

    currencies = list(Currency)
    _load_duplicates(currencies)
    for currency in currencies:
        unit_mapping.add(currency)
        add_stored_unit_to_regexes(currency, add_to_currency=not currency.should_exclude_symbol)


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
                                    context_cache: dict = None,
                                    squared: bool = False) -> ConversionResult:
    base = Conversion(Unit.from_stored_unit(base_stored_unit), value, squared=squared)
    to = []
    context_cache = context_cache or {}
    for code in await get_linked_codes(base, message, context_cache):
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

    def __init__(self, bot):
        super().__init__(bot)
        self._rebuilding = None

    @classmethod
    def base_measurement_to_conversion_result(cls, base_stored_unit: StoredUnit, value: float) -> ConversionResult:
        return base_measurement_to_conversion_result(base_stored_unit=base_stored_unit, value=value)

    def rebuild(self):
        self._rebuilding = True
        add_all_to_mapping()
        self._rebuilding = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.rebuild()
        self.start_task(self.currency_rate_updater, check=self.bot.production)

    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name='add', description='Add a currency you\'d like to enable converting.')
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

    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @app_commands.command(name='server_add',
                          description='Add a currency you\'d like to enable converting server-wide.')
    async def server_add(self, interaction: discord.Interaction, currency_code: str):
        currency_code = currency_code.upper()
        currency = Currency.get_or_none(code=currency_code)
        if currency is None:
            await interaction.response.send_message('This currency doesn\'t exist.')
            return
        try:
            ServerCurrency.create(currency=currency, guild_id=interaction.guild_id)
        except peewee.IntegrityError:
            await interaction.response.send_message('This currency is already added to this server.')
            return
        current = [x.code for x in Currency.select(Currency.code).join(ServerCurrency).where(ServerCurrency.guild_id == interaction.guild_id)]
        await interaction.response.send_message('OK, current (server wide) currencies: ' + ', '.join(current))

    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @app_commands.command(name='server_remove',
                          description='Remove a currency from the server-wide currency list.')
    async def server_remove(self, interaction: discord.Interaction, currency_code: str):
        currency_code = currency_code.upper()
        currency = Currency.get_or_none(code=currency_code)
        if currency is None:
            await interaction.response.send_message('This currency doesn\'t exist.')
            return

        delete_count = ServerCurrency.delete() \
            .where(ServerCurrency.guild_id == interaction.guild_id) \
            .where(ServerCurrency.currency == currency) \
            .execute()
        if delete_count == 0:
            await interaction.response.send_message('This currency was not added to this server.')
            return
        current = [x.code for x in Currency.select(Currency.code).join(ServerCurrency).where(ServerCurrency.guild_id == interaction.guild_id)]
        await interaction.response.send_message('OK, current (server wide) currencies: ' + ', '.join(current))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # if not self.bot.production:
        #     return

        if message.author.bot or "http" in message.content:
            return

        if self._rebuilding:
            print('rebuilding...')
            return

        conversion_results = []

        for unit_value, value in measurement_regex.match(message.content.lower()):
            squared = False
            if "sq" in unit_value:
                unit_value = unit_value.replace("sq", "")
                squared = True
            for unit in unit_mapping.get_units(unit_value):
                conversion_result = await base_to_conversion_result(unit, value, message, squared=squared)
                conversion_results.append(conversion_result)

        for unit_value, value in currency_regex.match(message.content.lower()):
            filter = None
            cache = None
            if unit_value in CurrencyCache.symbols_with_duplicates:
                allowed_codes = list(map(str.lower, await fetch_context_currency_codes(message)))
                cache = {message.id: allowed_codes}
                filter = lambda u: u.code.lower() in allowed_codes

            for unit in unit_mapping.get_units(unit_value, filter=filter):
                conversion_result = await base_to_conversion_result(unit, value, message, context_cache=cache, squared=False)
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
