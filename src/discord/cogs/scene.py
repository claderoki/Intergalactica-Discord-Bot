import random
import asyncio

import discord
from discord.ext import commands

import src.config as config
from src.models import Scene, Scenario, database
from src.discord.helpers.waiters import *
from src.games.game.base import DiscordIdentity
from src.discord.cogs.core import BaseCog

class SceneCog(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.message_count = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

    async def perform_scenario(self, ctx):
        identity = DiscordIdentity(ctx.author)
        scene = Scene.get(command_name = ctx.command.name)
        await scene.send(ctx, identity = identity)

    @commands.command()
    async def addscene(self, ctx, group, name):
        Scene.get_or_create(command_name = name, group_name = group)
        await ctx.send("OK. Created.")

    @commands.command()
    async def addscenarios(self, ctx, group, name):
        prompt = lambda x : ctx.translate(f"scenario_{x}_prompt")

        scene, _ = Scene.get_or_create(command_name = name, group_name = group)

        while True:
            scenario = Scenario(scene = scene)

            waiter = StrWaiter(ctx, prompt = prompt("text"), max_words = None, skippable = True)
            try:
                scenario.text = await waiter.wait()
            except Skipped:
                return await ctx.send("Okay. I'll stop now.")

            waiter = FloatWaiter(ctx, prompt = prompt("probability"), skippable = True)
            try:
                scenario.probability = await waiter.wait()
            except Skipped:
                return await ctx.send("Okay. I'll stop now.")

            waiter = RangeWaiter(ctx, prompt = prompt("range"), skippable = True)
            try:
                scenario.range = await waiter.wait()
            except Skipped:
                return await ctx.send("Okay. I'll stop now.")

            scenario.save()
            await ctx.send("Okay. This scenario has been created.")

def setup(bot):
    bot.add_cog(SceneCog(bot))