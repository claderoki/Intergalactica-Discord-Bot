from enum import Enum

import peewee
import discord

from .base import BaseModel, JsonField, EnumField
import src.config as config

class SubredditField(peewee.TextField):
    def db_value(self, value):
        if value is not None:
            return value.display_name

    def python_value(self, value):
        if value is not None:
            return config.bot.reddit.subreddit(value)

class Subreddit(BaseModel):
    history_limit = 15

    class PostType(Enum):
        top = 0
        new = 1
        hot = 2

    class EmbedType(Enum):
        full  = 0
        basic = 1

    guild_id    = peewee.BigIntegerField (null = True)
    channel_id  = peewee.BigIntegerField (null = True)
    user_id     = peewee.BigIntegerField (null = False)
    subreddit   = SubredditField         (null = False)
    url_history = JsonField              (null = False, default = lambda : [] )
    post_type   = EnumField              (PostType, null = False, default = PostType.top)
    embed_type  = EnumField              (EmbedType, null = False, default = EmbedType.full)
    dm          = peewee.BooleanField    (null = False, default = False)
    automatic   = peewee.BooleanField    (null = False, default = True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subreddit = None

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    @property
    def sendable(self):
        return self.channel if not self.dm else self.user

    async def send(self):
        try:
            post = self.latest_post
        except Exception as e:
            print("Failed to send reddit", e)
            return

        if post is None:
            return

        args = []
        kwargs = {}

        embed = self.get_post_embed(post)
        if embed is None:
            lines = [post.url, f"<https://reddit.com{post.permalink}>", post.title]
            args.append("\n".join(lines))
        else:
            kwargs["embed"] = embed
        sendable = self.sendable
        if sendable is not None:
            try:
                await self.sendable.send(*args, **kwargs)
            except discord.errors.Forbidden:
                return

    @property
    def latest_post(self):
        submissions = getattr(self.subreddit, self.post_type.name)(limit = 5)

        for submission in submissions:
            if submission.stickied:
                continue

            # if submission.over_18 and not self.channel.is_nsfw():
            #     continue

            if len(self.url_history) >= self.history_limit:
                self.url_history = self.url_history[-(self.history_limit-1):]

            if submission.url in self.url_history:
                continue

            self.url_history.append(submission.url)
            self.save(only = [Subreddit.url_history])
            return submission

    def __post_is_image(self, post):
        if hasattr(post, "post_hint") and post.post_hint == "image":
            return True
        if post.url[-3:] in ("jpg", "png"):
            return True
        if post.url.startswith("https://imgur.com/a"):
            post.url += ".jpg"
            return True
        return False

    def get_post_embed(self, post):
        embed = discord.Embed(color = self.bot.get_dominant_color(self.guild))
        if post.selftext:
            embed.description = post.selftext[:2000]
        elif self.__post_is_image(post):
            embed.set_image(url = post.url)
        else:
            return None

        if self.embed_type == self.EmbedType.full:
            embed.set_author(name = "".join(post.title[:255]), url = post.shortlink)
            embed.set_footer(text = post.subreddit_name_prefixed)

        return embed