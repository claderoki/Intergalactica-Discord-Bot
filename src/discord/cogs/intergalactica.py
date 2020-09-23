import asyncio

import discord
from discord.ext import commands

# from src.models import Human, database as db
# import src.config as config

class Intergalactica(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # self.poll.start()
        pass

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def purgeintros(self, ctx):
        channel = ctx.guild.get_channel(742567349613232249)

        coros = []
        async for message in channel.history(limit=200):
            if not isinstance(message.author, discord.Member):
                embed = discord.Embed(
                    color = ctx.guild_color,
                    title = f"Introduction by {message.author}",
                    description = message.content)
                coros.append( ctx.send(embed = embed) )

                await message.delete()

        if len(coros) == 0:
            embed = discord.Embed(title ="Nothing to purge.", color = ctx.guild_color)
            coros.append( ctx.send(embed = embed) )

        asyncio.gather(*coros)
            


def setup(bot):
    bot.add_cog(Intergalactica(bot))