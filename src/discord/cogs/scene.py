import random

import discord
from discord.ext import commands

import src.config as config
from src.models import Scene, Scenario, database
from src.discord.helpers.waiters import *
from src.games.game.base import DiscordIdentity


class SceneCog(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.group()
    async def pigeon(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            # with database:
            #     Scene.select().where(Scene.group_name == ctx.command.name)

    async def perform_scenario(self, ctx):
        with database:
            identity = DiscordIdentity(ctx.author)
            scene = Scene.get(command_name = ctx.command.name)
            await scene.send(ctx, identity = identity)

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "feed")
    async def pigeon_feed(self, ctx):
        await self.perform_scenario(ctx)

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "yell")
    async def pigeon_yell(self, ctx):
        await self.perform_scenario(ctx)

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "chase")
    async def pigeon_chase(self, ctx):
        await self.perform_scenario(ctx)

    @commands.command()
    async def addscene(self, ctx, group, name):
        with database:
            Scene.get_or_create(command_name = name, group_name = group)
        await ctx.send("OK. Created.")

    @commands.command()
    async def addscenarios(self, ctx, group, name):
        with database:
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