import random
import asyncio

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
        self.message_count = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guilds = {742146159711092757: 742163352712642600,
            761624318291476482:766643537269751849}

        guild = message.guild
        if guild.id not in guilds:
            return
        
        channel_id = guilds[guild.id]
        if message.channel.id == channel_id:
            self.message_count += 1
            print(self.message_count)
            command = self.bot.command_prefix + "pigeon claim"
            if message.content == command:
                return
            if random.randint(self.message_count, 1000) >= 950:
                self.message_count = 0
                embed = discord.Embed(color = self.bot.get_dominant_color(message.guild))
                embed.title = "💩 Pigeon Droppings 💩"
                embed.description = f"Pigeon dropped something in chat! Type **{command}** it find out what it is."
                embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
                await message.channel.send(embed = embed)

                def check(m):
                    return m.content.lower() == command and m.channel.id == channel_id and not m.author.bot
                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60)
                except asyncio.TimeoutError:
                    embed = discord.Embed(color = self.bot.get_dominant_color(message.guild))
                    embed.title = "💩 Pigeon Droppings 💩"
                    embed.description = f"The pigeon kept its droppings to itself."
                    embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
                    await message.channel.send(embed = embed)
                else:
                    author = msg.author
                    embed = discord.Embed(color = self.bot.get_dominant_color(message.guild))
                    embed.title = "💩 Pigeon Droppings 💩"
                    money = random.randint(0, 100)
                    embed.description = f"{author.mention}, you picked up the droppings and received {self.bot.gold_emoji} {money}"
                    embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
                    await message.channel.send(embed = embed)
                    identity = DiscordIdentity(message.author)
                    identity.add_points(money)

    @commands.group()
    async def pigeon(self, ctx):
        pass

    async def perform_scenario(self, ctx):
        with database:
            identity = DiscordIdentity(ctx.author)
            scene = Scene.get(command_name = ctx.command.name)
            await scene.send(ctx, identity = identity)

    @pigeon.command(name = "help")
    async def pigeon_help(self, ctx):
        embed_data = {
            "title": "⋆ Broken Pigeon-Phone ⋆",
            "description": "**__Money Generator__**\n• /pigeon feed\n• /pigeon chase\n• /pigeon yell\n• /pigeon fish\n\n**__Interactive__**\n• /pigeon claim: Droppings spawn randomly. Input claim to collect it.\n• /pigeon buy: Purchase a pigeon for Pigeon Fight.\n• /pigeon fight: \n",
            "footer": {
                "text": "There is a 4h cooldown for all Money Generator commands.",
                "icon_url": "https://cdn.discordapp.com/attachments/705242963550404658/766661638224216114/pigeon.png"
            }
        }

        embed = discord.Embed.from_dict(embed_data)
        embed.color = ctx.guild_color
        await ctx.send(embed = embed)

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

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "fish")
    async def pigeon_fish(self, ctx):
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