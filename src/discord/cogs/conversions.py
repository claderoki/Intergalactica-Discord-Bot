import re
import asyncio
import datetime
import pytz

import discord
from currency_converter import CurrencyConverter
import pycountry
from measurement.utils import guess
from measurement.measures import Distance, Temperature, Volume, Weight

import src.config as config
from src.discord.helpers.converters import convert_to_time
from src.models import Human, database

class Conversion:
    pass

class CurrencyConversion(Conversion):
    pass
class TimezoneConversion(Conversion):
    pass
class MeasurementConversion(Conversion):
    pass

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

currency_symbols = {"usd": "$", "gbp": "£", "eur": "€"}

units = {
    "f"      : "°F",
    "c"      : "°C",
    "inch"   : '"',
    "us_cup" : "cup",
}
for alpha_2, symbol in currency_symbols.items():
    units[alpha_2] = symbol

def clean_value(value):
    return int(value) if value % 1 == 0 else round(value, 2)

def clean_measurement(value, unit = None):
    if unit is None:
        unit = value.unit
        value = value.value

    value = clean_value(value)

    return str(value) + units.get(unit, unit)

all_units = list(other_measurements.keys())
all_units.append("°f")
all_units.append("°c")
all_units.append('"')
all_units.append('cup')

currency_converter = CurrencyConverter()

class ConversionCog(discord.ext.commands.Cog, name = "Conversion"):
    measures = (Weight, Temperature, Distance, Volume)
    time_format = "%H:%M (%I%p)"

    def __init__(self, bot):
        super().__init__()

        _units = all_units
        currency_regex_symbols = []
        for symbol in currency_symbols.values():
            if symbol == "$":
                currency_regex_symbols.append("\$")
            else:
                currency_regex_symbols.append(symbol)

        for  currency in currency_converter.currencies:
            _units.append(currency.lower())
        _units += currency_regex_symbols

        self.global_pattern = "([+-]?\d+(\.\d+)*)({})(?!\w)".format("|".join(_units))
        self.currency_pattern = "({})(\d+(\.\d+)*)(?!\w)".format("|".join(currency_regex_symbols))

        self.bot = bot
        self.currency_converter = currency_converter

    def convert(self, member, currencies, measurements):
        color = self.bot.get_dominant_color(None)
        embed = discord.Embed(color = color)

        for measurement in measurements:
            values = []
            for other in other_measurements[measurement.unit]:
                value = getattr(measurement, other)
                values.append(clean_measurement(value, other))
            embed.add_field(name = clean_measurement(measurement), value = "\n".join(values))

        if len(currencies) > 0:
            human, _ = Human.get_or_create(user_id = member.id)
            for currency in currencies:
                values = []
                for other in (x for x in human.all_currencies if x.alpha_3 != currency.alpha_3):
                    try:
                        converted = clean_value(self.currency_converter.convert(currencies[currency], currency.alpha_3, other.alpha_3))
                    except ValueError:
                        continue
                    values.append(f"{other.name} {converted}")
                if len(values) > 0:
                    embed.add_field(name = currency.name, value = "\n".join(values))
        if len(embed.fields) > 0:
            return embed

    def _get_matches(self, content):
        cleaned_matches = []

        matches = re.findall(self.global_pattern, content)
        if matches:
            for match in matches:
                value = float(match[0])
                unit = match[-1]
                for _unit, alias in units.items():
                    if alias.lower() == unit:
                        unit = _unit
                cleaned_matches.append({"value" : value, "unit" : unit})

        matches = re.findall(self.currency_pattern, content)
        if matches:
            for match in matches:
                symbol = match[0]
                value = match[1]
                if symbol == "$":
                    cleaned_matches.append({"value" : value, "unit" : "usd"})
                    cleaned_matches.append({"value" : value, "unit" : "cad"})
                else:
                    for alpha_2, _symbol in currency_symbols.items():
                        if symbol == _symbol:
                            unit = alpha_2.lower()
                            break
                    cleaned_matches.append({"value" : value, "unit" : unit})

        return cleaned_matches

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.bot.production:
            return

        if "http" in message.content:
            return

        matches = self._get_matches(message.content.lower())
        if len(matches):
            measurements = []
            currencies   = {}
            for match in matches:
                unit, value = match["unit"], match["value"]
                if unit.upper() in self.currency_converter.currencies:
                    currencies[(pycountry.currencies.get(alpha_3 = unit.upper()))] = value
                else:
                    measurements.append(guess(value, unit, measures = self.measures))

            embed = self.convert(message.author, currencies, measurements)
            if embed is not None:
                asyncio.gather(message.channel.send(embed = embed))

        elif "utc" in message.content.lower() or "gmt" in message.content.lower():
            times = {}
            for word in message.content.lower().split():
                if word.startswith("utc") or word.startswith("gmt"):
                    timezone = word[:3]
                    remaining = word.replace(timezone, "")
                    now = datetime.datetime.now(pytz.timezone(timezone))
                    if remaining == "":
                        symbol = "+"
                        numbers = 0
                    else:
                        symbol = remaining[0]
                        numbers = int("".join(x for x in remaining[1:] if x.isdigit()))
                    if symbol == "+":
                        times[f"{timezone}{symbol}{numbers}"] = now + datetime.timedelta(hours = numbers)
                    elif symbol == "-":
                        times[f"{timezone}{symbol}{numbers}"] = now - datetime.timedelta(hours = numbers)

                    embed = discord.Embed(color = self.bot.get_dominant_color(message.guild))
                    for timezone, time in times.items():
                        embed.add_field(name = timezone.upper(), value = time.strftime("%H:%M"))
                    asyncio.gather(message.channel.send(embed = embed))

        else:
            time = convert_to_time(message.content.lower())
            if time is not None:
                human, _ = Human.get_or_create(user_id = message.author.id)
                if human.timezone is not None:
                    tz = pytz.timezone(human.timezone)
                    local_time = tz.localize(datetime.datetime(2020,11,28, hour = time.hour, minute = time.minute))
                    users_added = [human.user_id]

                    embed = discord.Embed(color = self.bot.get_dominant_color(None))
                    embed.title = f"{time.strftime(self.time_format)} for {message.author}"
                    embed.set_footer(text = "React to show your time.")
                    embed_message = await message.channel.send(embed = embed)
                    try:
                        await self.bot.wait_for("reaction_add", timeout = 360, check = self.__check(embed_message, local_time, users_added))
                    except asyncio.TimeoutError:
                        asyncio.gather(embed_message.clear_reactions())

    def __check(self, message, local_time, users_added):
        emoji = "✅"
        asyncio.gather(message.add_reaction(emoji))

        def _check(reaction, user):
            if str(reaction.emoji) == emoji and reaction.message.id == message.id and user.id not in users_added:
                human, _ = Human.get_or_create(user_id = user.id)
                if human.timezone is not None:
                    time = local_time.astimezone(pytz.timezone(human.timezone))
                    embed = message.embeds[0]
                    embed.add_field(name = f"{human.user}", value = time.strftime(self.time_format))
                    asyncio.gather(message.edit(embed = embed))
                    users_added.append(user.id)

        return _check


def setup(bot):
    bot.add_cog(ConversionCog(bot))