import re

import discord
from measurement.utils import guess
from measurement.measures import Distance, Temperature, Volume, Weight

import src.config as config

measurements = [
    ("c", "f"),
    ("kg", "lb"),
    ("g", "oz"),
    ("cm", "inch", "ft"),
    ("ml", "cup"),
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

def clean_measurement(value, unit = None):
    if unit is None:
        unit = value.unit
        value = value.value

    value = int(value) if value % 1 == 0 else round(value, 2)

    return str(value) + units.get(unit, unit)

all_units = list(other_measurements.keys())
all_units.append("°f")
all_units.append("°c")
all_units.append('"')

class Conversions(discord.ext.commands.Cog):
    measures = (Weight, Temperature, Distance)
    global_pattern = '([+-]?\d+(\.\d+)*)({})(?!\w)'.format("|".join(all_units))

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not self.production:
            return


        if "http" in message.content:
            return

        color = self.bot.get_dominant_color(message.guild)

        matches = re.findall(self.global_pattern, message.content.lower())
        if matches:

            measurements = []
            for match in matches:
                value = float(match[0])
                unit = match[-1].replace("°", "").replace('"', "in")
                measurement = guess(value, unit, measures = self.measures)
                measurements.append(measurement)

            embed = discord.Embed(title = "Conversions", color = color)

            for measurement in measurements:
                values = []
                for other in other_measurements[measurement.unit]:
                    value = getattr(measurement, other)
                    values.append(clean_measurement(value, other))
                if len(measurements) == 1 and len(values) == 1:
                    try:
                        raise Exception()
                        await self.bot.spell_reaction(message, f"{values[0].replace('°', '')}")
                    except Exception as e:
                        await message.channel.send(embed = discord.Embed(description = f"{clean_measurement(measurement)} = {values[0]}", color = color))
                    return

                else:
                    embed.add_field(name = clean_measurement(measurement), value = "\n".join(values) )

            await message.channel.send(embed = embed)

def setup(bot):
    bot.add_cog(Conversions(bot))