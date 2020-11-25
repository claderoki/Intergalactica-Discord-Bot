import re
import asyncio

import discord
from currency_converter import CurrencyConverter
import pycountry
from measurement.utils import guess
from measurement.measures import Distance, Temperature, Volume, Weight

import src.config as config
from src.models import Human, database

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

units = \
{
    "f" : "°F",
    "c" : "°C",
    "inch" : '"'
}

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

currency_converter = CurrencyConverter()

class Conversions(discord.ext.commands.Cog):
    measures = (Weight, Temperature, Distance, Volume)
    global_pattern = '([+-]?\d+(\.\d+)*)({})(?!\w)'.format("|".join(all_units + [x.lower() for x in currency_converter.currencies] ))

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.currency_converter = currency_converter

    def convert(self, member, currencies, measurements):
        color = self.bot.get_dominant_color(member.guild)
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

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.bot.production:
            return

        if "http" in message.content:
            return

        matches = re.findall(self.global_pattern, message.content.lower())
        if matches:
            measurements = []
            currencies   = {}
            for match in matches:
                value = float(match[0])
                unit = match[-1].replace("°", "").replace('"', "in")
                if unit.upper() in self.currency_converter.currencies:
                    currencies[(pycountry.currencies.get(alpha_3 = unit.upper()))] = value
                else:
                    measurements.append(guess(value, unit, measures = self.measures))

            embed = self.convert(message.author, currencies, measurements)
            if embed is not None:
                asyncio.gather(message.channel.send(embed = embed))

def setup(bot):
    bot.add_cog(Conversions(bot))