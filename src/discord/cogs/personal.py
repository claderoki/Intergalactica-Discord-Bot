import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
# from src.models import SavedEmoji, Human, database
# from src.discord.errors.base import SendableException
try:
    import cv2
except:
    pass

class Personal(discord.ext.commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(60 * 60)
        self.water_reminder.start()

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @commands.command()
    async def crna(self, ctx):
        if self.bot.production:
            return

        if ctx.author.id in (120566758091259906, 396362827822268416):
            async with ctx.typing():
                cam = cv2.VideoCapture(0)
                frame = cam.read()[1]
                await asyncio.sleep(15)
                frame = cam.read()[1]
                full_path = f"{config.path}/tmp/frame.png"
                cv2.imwrite(full_path, frame)
                cam.release()
                url = await self.bot.store_file(full_path, "frame.png")
                await ctx.send(url)

    @commands.is_owner()
    @commands.command()
    async def dm(self, ctx, user : discord.User):
        await user.send("ok")

    @tasks.loop(hours = 1)
    async def water_reminder(self):
        channel = self.bot.get_channel(755895328745455746)
        await channel.send(f"<@{396362827822268416}> drink water!")

def setup(bot):
    bot.add_cog(Personal(bot))