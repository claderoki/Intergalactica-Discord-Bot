import random

import discord
import peewee

from .base import BaseModel, JsonField, EnumField

class Scene(BaseModel):
    command_name         = peewee.CharField(column_name = "name", unique = True, max_length = 100)
    group_name           = peewee.CharField(column_name = "command_name",   max_length = 100)

    def get_random(self):
        scenarios = self.scenarios
        return random.choices(scenarios, weights = [x.probability for x in scenarios], k = 1)[0]

    async def send(self, ctx, identity):
        scenario = self.get_random()
        money = scenario.random_value
        embed = discord.Embed(color = ctx.guild_color)
        embed.description = scenario.text
        if self.group_name == "pigeon":
            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        if money > 0:
            embed.description += f" You earn {self.bot.gold_emoji} {abs(money)}"
        elif money < 0:
            embed.description += f" You lose {self.bot.gold_emoji} {abs(money)}"

        identity.add_points(money)
        await ctx.send(embed = embed)

class Scenario(BaseModel):
    text        = peewee.TextField        (null = False)
    probability = peewee.FloatField       (null = False)
    min         = peewee.IntegerField     (null = False)
    max         = peewee.IntegerField     (null = False)
    scene       = peewee.ForeignKeyField  (Scene, backref = "scenarios", on_delete = "CASCADE")

    @property
    def random_value(self):
        return random.randint(self.min, self.max)

    @property
    def range(self):
        pass

    @range.setter
    def range(self, value):
        self.min = value.start
        self.max = value.stop