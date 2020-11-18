import asyncio
import io
import os

import discord
from discord.ext import commands, tasks
# import win10toast

import src.config as config
# from src.models import SavedEmoji, Human, database
# from src.discord.errors.base import SendableException
if not config.bot.production:
    import cv2
    from notifypy import Notify

class Personal(discord.ext.commands.Cog):
    crna_id = 396362827822268416
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            await asyncio.sleep(60 * 60)
            self.water_reminder.start()
        else:
            pass

    def notify(self, block = True, **kwargs):
        notification = Notify()
        for key, value in kwargs.items():
            setattr(notification, key, value)

        notification.send(block = block)

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @commands.command(name = "notify")
    async def notify_command(self, ctx, *, message):
        if self.bot.production:
            return

        if ctx.author.id in (self.bot.owner_id, self.crna_id):

            icon_path = f"{config.path}/tmp/{ctx.author.id}.png"
            if not os.path.exists(icon_path):
                asset = ctx.author.avatar_url_as(size = 64)
                await asset.save(icon_path)

            notification = Notify()
            notification.title = f"Message from {ctx.author}"
            notification.message = message
            notification.icon = icon_path
            notification.application_name = None
            notification.send(block = False)
            asyncio.gather(ctx.send("Sent!"))

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @commands.command()
    async def crna(self, ctx):
        if self.bot.production:
            return

        if ctx.author.id in (self.bot.owner_id, self.crna_id):
            async with ctx.typing():
                cam = cv2.VideoCapture(0)
                frame = cam.read()[1]
                self.notify(title = "Snapshot", message = "About to take a snapshot!", block = False)
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
        await channel.send(f"<@{self.crna_id}> drink water!")

def setup(bot):
    bot.add_cog(Personal(bot))