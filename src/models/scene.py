import random

import discord
import peewee

from .base import BaseModel


class Scene(BaseModel):
    command_name = peewee.CharField(column_name="name", unique=True, max_length=100)
    group_name = peewee.CharField(column_name="command_name", max_length=100)

    async def send(self, ctx, human):
        scenario = self.get_random_scenario(scene=self)
        money = scenario.random_value
        embed = discord.Embed(color=ctx.guild_color)
        embed.description = scenario.text
        if self.group_name == "pigeon":
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        if money > 0:
            embed.description += f" You earn {self.bot.gold_emoji} {abs(money)}"
        elif money < 0:
            embed.description += f" You lose {self.bot.gold_emoji} {abs(money)}"

        human.gold += money
        await ctx.send(embed=embed)


class Scenario(BaseModel):
    text = peewee.TextField(null=False)
    probability = peewee.FloatField(null=False)
    min = peewee.IntegerField(null=False)
    max = peewee.IntegerField(null=False)
    scene = peewee.ForeignKeyField(Scene, backref="scenarios", on_delete="CASCADE")

    @classmethod
    def get_random(cls, scene=None, win=False):
        query = """
            SELECT results.* FROM (
            SELECT {table_name}.*, @running_total AS previous_total, @running_total := @running_total + {chance_column_name} AS running_total, until.rand
            FROM (
                SELECT round(rand() * init.max) AS rand FROM (
                SELECT sum({chance_column_name}) - 1 AS max FROM {table_name} {where}
                ) AS init
            ) AS until,
            (SELECT * FROM {table_name} {where}) AS {table_name},
            ( SELECT @running_total := 0.00 ) AS vars
            ) AS results
            WHERE results.rand >= results.previous_total AND results.rand < results.running_total;
        """

        where = "WHERE 1 = 1 "

        if scene is not None:
            where += f"AND scene_id = {scene.id} "
        where += f"AND min " + (">" if win else "<") + " 0"

        query = query.format(
            table_name=cls._meta.table_name,
            where=where,
            chance_column_name="probability"
        )

        for scenario in cls.raw(query):
            return scenario

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
