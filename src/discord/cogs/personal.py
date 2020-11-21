import asyncio
import os
import datetime
import random

import discord
from discord.ext import commands, tasks

import src.config as config
if not config.bot.production:
    import cv2
    from notifypy import Notify

def is_permitted():
    def predicate(ctx):
        return ctx.author.id in (ctx.bot.owner.id, ctx.cog.user_id)
    return commands.check(predicate)

class Personal(discord.ext.commands.Cog):
    user_id = 396362827822268416
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.user = self.bot.get_user(self.user_id)
        if self.bot.production:
            await asyncio.sleep(60 * 60)
            self.water_reminder.start()

    def notify(self, block = True, **kwargs):
        notification = Notify()
        for key, value in kwargs.items():
            setattr(notification, key, value)

        notification.send(block = block)

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @is_permitted()
    @commands.command(name = "notify")
    async def notify_command(self, ctx, *, message):
        if self.bot.production:
            return

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
    @is_permitted()
    @commands.command()
    async def crna(self, ctx):
        if self.bot.production:
            return

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
    @commands.dm_only()
    @is_permitted()
    @commands.command()
    async def dm(self, ctx, *, text):
        if text == "":
            text = "empty"
        await self.user.send(text)

    @tasks.loop(hours = 1)
    async def water_reminder(self):
        if datetime.datetime.utcnow().hour not in range(16, 23):
            messages = [
                "Hey {mention}! Drink some water right now!",
                "Hello, {mention}. Might I interest you in some water?",
                "Hi there, {mention}. I believe it is time for you to drink some liquid.",
                "Ah, I didn't see you there, {mention}. Greetings. Have you drank water yet?",
            ]
            channel = self.bot.get_channel(755895328745455746)
            message = random.choice(messages).format(mention = self.user.mention)
            asyncio.gather(channel.send(message))

def setup(bot):
    bot.add_cog(Personal(bot))