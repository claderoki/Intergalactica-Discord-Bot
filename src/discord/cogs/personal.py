
from enum import Enum
import re
import asyncio
import string
import os
import datetime
import random

import discord
from discord.ext import commands, tasks

import src.config as config
from src.discord.errors.base import SendableException
from src.models import database, Subreddit, DailyReminder, Location, PersonalQuestion
from src.discord.cogs.core import BaseCog

def decode(text):
    decoded = []
    for word in text.split(" "):
        last_letter = None
        for letter in word:
            if last_letter != "." and last_letter is not None:
                index = int(last_letter + letter)-1
                decoded.append(string.ascii_lowercase[index])
                last_letter = None
            else:
                last_letter = letter
        decoded.append(" ")

    return "".join(decoded)

def encode(text, with_periods = True):
    encoded = []
    text = text.lower()

    for word in text.split(" "):
        for i, letter in enumerate(word):
            if letter in string.ascii_lowercase:
                index = string.ascii_lowercase.index(letter)+1
                encoded.append(str(index).zfill(2))
                if with_periods and i != len(word)-1:
                    encoded.append(".")
        encoded.append(" ")

    return "".join(encoded)

def is_permitted():
    def predicate(ctx):
        return ctx.author.id in (ctx.bot.owner.id, ctx.cog.user_id)
    return commands.check(predicate)

class Personal(BaseCog):
    user_id = 813612057098059779
    def __init__(self, bot):
        super().__init__(bot)
        self._user = None

    @property
    def user(self):
        if self._user is None:
            self._user = self.bot.get_user(self.user_id)
        return self._user

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.water_reminder, check = self.bot.production)
        self.start_task(self.free_games_notifier, check = self.bot.production)

    def notify(self, block = True, **kwargs):
        from notifypy import Notify
        notification = Notify()
        for key, value in kwargs.items():
            setattr(notification, key, value)

        notification.send(block = block)

    @commands.command()
    @is_permitted()
    async def secret(self, ctx, *, text):
        await ctx.send(encode(text))

    @commands.cooldown(1, 2, type=commands.BucketType.user)
    @commands.command()
    @is_permitted()
    async def ring(self, ctx):
        if self.bot.heroku:
            return

        from playsound import playsound
        playsound("resources/sounds/buzz.mp3")

    messages = []
    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @is_permitted()
    @commands.command(aliases = ["crna"])
    async def cam(self, ctx):
        if self.bot.heroku:
            return

        import cv2
        user = self.user if ctx.invoked_with == "crna" else ctx.author
        try:
            await ctx.send(self.messages.pop(0))
        except IndexError:
            pass

        async with ctx.typing():
            cam = cv2.VideoCapture(0)
            frame = cam.read()[1]
            self.notify(title = "Snapshot", message = "About to take a snapshot!", block = False)
            await asyncio.sleep(15)
            frame = cam.read()[1]
            full_path = f"{config.path}/tmp/frame.png"
            cv2.imwrite(full_path, frame)
            cam.release()
            url = await self.bot.store_file(full_path, "frame.png", owner = True)
            await user.send(url)

    @commands.command()
    @is_permitted()
    async def question(self, ctx, question : PersonalQuestion = None):
        if question is None:
            question = PersonalQuestion.get_random()
        if question is None or PersonalQuestion.select().where(PersonalQuestion.asked == False).count() == 0:
            raise SendableException(ctx.translate("all_questions_asked"))
        if question.asked:
            raise SendableException(ctx.translate("question_already_asked"))

        await ctx.send(embed = question.embed)
        question.asked = True
        question.save()

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
                if reminder.user:
                    asyncio.gather(reminder.user.send(reminder.text))
                reminder.last_reminded = now.date()
                reminder.save()
                break

    @tasks.loop(minutes = 1)
    async def free_games_notifier(self):
        ids = [742205149862428702]
        channels = [self.bot.get_channel(x) for x in ids]

        with database.connection_context():
            for subreddit in Subreddit.select().where(Subreddit.automatic == False):
                post = subreddit.latest_post

                if post is None:
                    return

                id = post.url.split("comments/")[1].split("/")[0]
                submission = self.bot.reddit.submission(id)

                skipped_channel_ids = []

                # try:
                game = FreeGame.from_reddit_submission(submission)
                embed = game.get_embed()
                if game.type not in (FreeGameType.steam, FreeGameType.gog, FreeGameType.epicgames, FreeGameType.unknown):
                    skipped_channel_ids.append(784439833975062546)
                # except Exception as e:
                #     print("FREE GAME: ",e)
                #     embed = discord.Embed(color = self.bot.get_dominant_color(None))
                #     embed.set_author(name = submission.title, url = post.url)
                #     embed.description = submission.url

                channels.append(subreddit.sendable)
                for channel in [x for x in channels if x.id not in skipped_channel_ids]:
                    asyncio.gather(channel.send(embed = embed))

def setup(bot):
    bot.add_cog(Personal(bot))

class FreeGameType(Enum):
    steam      = "https://cdn.discordapp.com/attachments/744172199770062899/826521425161617429/steam.png"
    gog        = "https://cdn.discordapp.com/attachments/744172199770062899/826523073032880148/gog.png"
    indiegala  = "https://cdn.discordapp.com/attachments/744172199770062899/826535828493828116/indie_gala.png"
    psn        = "https://cdn.discordapp.com/attachments/744172199770062899/826523389610033172/psn.png"
    epicgames  = "https://cdn.discordapp.com/attachments/744172199770062899/826521427914129458/epic_games.png"
    twitch     = "https://cdn.discordapp.com/attachments/744172199770062899/826521426836193405/twitch.png"
    unknown    = "https://cdn.discordapp.com/attachments/744172199770062899/826525145678086174/unknown.png"
    itchio     = "https://cdn.discordapp.com/attachments/744172199770062899/826864490053763122/itchio.png"

class FreeGame:
    __slots__ = ("name", "type", "url", "source")

    def __init__(self, name: str, type: FreeGameType, url: str, source: str):
        self.name   = name
        self.type   = type
        self.url    = url
        self.source = source

    @classmethod
    def from_reddit_submission(cls, submission):
        for match in re.findall(r"\[(.*?)\](.*)", submission.title):
            remaining = match[-1]
            for group in re.findall(r"(\(.*?\))", remaining):
                if "free" in group.lower() or "100" in group.lower():
                    remaining = remaining.replace(group, "")

            try:
                type = FreeGameType[match[0].lower().replace(" ", "").replace(".", "")]
            except KeyError:
                type = FreeGameType.unknown
            return cls(remaining.strip(), type, submission.url, submission.shortlink)

    def get_embed(self):
        embed = discord.Embed()
        embed.color = config.bot.get_dominant_color(None)
        embed.set_author(name = self.name, url = self.source, icon_url = self.type.value)
        embed.description = self.url
        return embed
