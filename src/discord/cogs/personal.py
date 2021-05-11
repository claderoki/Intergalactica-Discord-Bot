
from enum import Enum
import re
import asyncio
import string
import os
import datetime
import random

import discord
from discord.ext import commands, tasks
from weasyprint import HTML

import src.config as config
from src.discord.errors.base import SendableException
from src.models import database, Subreddit, DailyReminder, Location, PersonalQuestion
from src.discord.cogs.core import BaseCog
from src.discord.helpers.waiters import EnumWaiter

class WeekDays(Enum):
    weekend = 1
    week    = 2
    all     = 3

    def to_list(self):
        if self == WeekDays.weekend:
            return [6,7]
        elif self == WeekDays.week:
            return [1,2,3,4,5]
        elif self == WeekDays.all:
            return [1,2,3,4,5,6,7]

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
        authorized = ctx.author.id in (ctx.bot.owner.id, ctx.cog.user_id)
        return authorized and (ctx.guild is None or ctx.guild.member_count < 10)
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
        await asyncio.sleep(10)
        self.start_task(self.daily_reminders, check = True)
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

    async def generate_daily_stoic(self, now = None):
        folder = config.path + "/src/templates/DailyStoic"

        filename_format = "{day}-{month}.xhtml"
        z = lambda x : str(x).zfill(2)
        filename = filename_format.format(day = z(now.day), month = z(now.month))
        with open(f"{folder}/Text/{filename}", encoding = "utf-8") as f:
            html = HTML(string = f.read(), base_url = folder + "/Text")
            output_filename = filename.replace("xhtml", "png")
            output_path = f"{config.path}/tmp/daily-stoic/{output_filename}"
            html.write_png(output_path)
            return await self.bot.store_file(output_path, output_filename, owner = False)

    @commands.command()
    @is_permitted()
    async def stoic(self, ctx):
        human = ctx.get_human()
        now = human.current_time or datetime.datetime.utcnow()
        url = await self.generate_daily_stoic(now = now)
        await ctx.send(url)

    @commands.is_owner()
    @commands.dm_only()
    @is_permitted()
    @commands.command()
    async def dm(self, ctx, *, text):
        if text == "":
            text = "empty"
        await self.user.send(text)

    @commands.group(name = "dailyreminder")
    @is_permitted()
    async def daily_reminder(self, ctx):
        pass

    @daily_reminder.command(name = "create")
    async def daily_reminder_create(self, ctx):
        reminder = DailyReminder(user_id = ctx.author.id)
        await reminder.editor_for(ctx, "type")
        if reminder.type == DailyReminder.ReminderType.text:
            await reminder.editor_for(ctx, "value", skippable = False)
        await reminder.editor_for(ctx, "time")
        await reminder.editor_for(ctx, "time_type")

        waiter = EnumWaiter(ctx, WeekDays, prompt = "daily_reminder_week_days_prompt")
        weekdays = await waiter.wait()
        reminder.week_days = weekdays.to_list()

        reminder.save()
        await ctx.success(ctx.translate("daily_reminder_created"))

    @tasks.loop(seconds = 10)
    async def daily_reminders(self):
        query = DailyReminder.select()
        query = query.order_by(DailyReminder.time.desc())

        if self.bot.heroku:
            query = query.where(DailyReminder.type == DailyReminder.ReminderType.text)
        elif not self.bot.production:
            query = query.where(DailyReminder.type == DailyReminder.ReminderType.stoic)

        for reminder in DailyReminder:
            if reminder.time_type == DailyReminder.TimeType.utc:
                now = datetime.datetime.utcnow()
            elif reminder.time_type == DailyReminder.TimeType.local:
                human = self.bot.get_human(user = reminder.user_id)
                now = human.current_time or datetime.datetime.utcnow()
            else:
                continue
            if now.weekday()+1 not in reminder.week_days:
                continue
            if reminder.time > now.time():
                continue
            if reminder.time.hour != now.hour:
                continue

            if reminder.last_reminded != now.date():
                content = reminder.value or ""

                if reminder.type == DailyReminder.ReminderType.stoic:
                    content += "\n" + await self.generate_daily_stoic(now = now)
                user = reminder.user
                if user:
                    asyncio.gather(reminder.user.send(content))
                reminder.last_reminded = now.date()
                reminder.save()

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

                game = FreeGame.from_reddit_submission(submission)
                embed = game.get_embed()
                if game.type not in (FreeGameType.steam, FreeGameType.gog, FreeGameType.epicgames, FreeGameType.unknown):
                    skipped_channel_ids.append(784439833975062546)

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
