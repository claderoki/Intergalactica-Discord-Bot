import asyncio
import os
import datetime
import random

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import database, Subreddit, DailyReminder, Location

if not config.bot.heroku:
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
        self._user = None

    @property
    def user(self):
        if self._user is None:
            self._user = self.bot.get_user(self.user_id)
        return self._user

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.water_reminder.start()
            self.free_games_notifier.start()
            # await asyncio.sleep(60 * 60)

    def notify(self, block = True, **kwargs):
        notification = Notify()
        for key, value in kwargs.items():
            setattr(notification, key, value)

        notification.send(block = block)

    @commands.cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @is_permitted()
    async def ring(self, ctx):
        if self.bot.heroku:
            return

        from playsound import playsound
        playsound("resources/sounds/buzz.mp3")

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @is_permitted()
    @commands.command(name = "notify")
    async def notify_command(self, ctx, *, message):
        if self.bot.heroku:
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

    @commands.dm_only()
    @is_permitted()
    @commands.command()
    async def gps(self, ctx):
        last_location = Location.select().where(Location.name == "Clark").order_by(Location.created_on.desc()).first()
        url = last_location.google_maps_url

        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.description = f"[Google maps url]({url})"
        embed.set_footer(text = "Last seen at")
        embed.timestamp = last_location.created_on
        asyncio.gather(ctx.send(embed = embed))

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @is_permitted()
    @commands.command()
    async def crna(self, ctx, user : discord.User = None):
        if self.bot.heroku:
            return

        user = user or ctx.author
        if user.id not in (ctx.bot.owner.id, ctx.cog.user_id):
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
            await user.send(url)

    @commands.is_owner()
    @commands.dm_only()
    @is_permitted()
    @commands.command()
    async def dm(self, ctx, *, text):
        if text == "":
            text = "empty"
        await self.user.send(text)

    @tasks.loop(seconds = 10)
    async def water_reminder(self):
        now = datetime.datetime.utcnow()
        weekend = now.weekday() in range(5, 7)
        weekday = not weekend

        query = DailyReminder.select()
        query = query.where(DailyReminder.time <= now.time())
        query = query.where(DailyReminder.time.hour == now.time().hour)
        query = query.where( (DailyReminder.weekday == weekday) | (DailyReminder.weekend == weekend) )
        query = query.order_by(DailyReminder.time.desc())

        for reminder in query:
            if reminder.last_reminded != now.date():
                asyncio.gather(reminder.user.send(reminder.text))
                reminder.last_reminded = now.date()
                reminder.save()
                break

    @tasks.loop(minutes = 1)
    async def free_games_notifier(self):
        extra_games_channel = self.bot.get_channel(742205149862428702)

        with database.connection_context():
            for subreddit in Subreddit.select().where(Subreddit.automatic == False):
                post = subreddit.latest_post

                if post is None:
                    return

                id = post.url.split("comments/")[1].split("/")[0]
                submission = self.bot.reddit.submission(id)

                embed = discord.Embed(color = self.bot.get_dominant_color(None))
                embed.set_author(name = submission.title, url = post.url)
                embed.description = submission.url
                asyncio.gather(subreddit.sendable.send(embed = embed))

                if extra_games_channel is not None:
                    asyncio.gather(extra_games_channel.send(embed = embed))



def setup(bot):
    bot.add_cog(Personal(bot))