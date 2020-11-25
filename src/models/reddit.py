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
    class PostType(Enum):
        top = 0
        new = 1
        hot = 2

    history_limit = 3

    guild_id    = peewee.BigIntegerField()
    channel_id  = peewee.BigIntegerField()
    subreddit   = SubredditField()
    url_history = JsonField(default = lambda : [] )
    post_type   = EnumField(PostType, default = PostType.top)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subreddit = None

    async def send(self):
        if self.guild is None or self.channel is None:
            return

        post = self.latest_post

        if post is None:
            return

        if post.over_18 and not self.channel.is_nsfw():
            return

        embed = self.get_post_embed(post)

        if embed is None:
            lines = [post.url, f"<https://reddit.com{post.permalink}>", post.title]
            await self.channel.send("\n".join(lines))
        else:
            await self.channel.send(embed = embed)

    @property
    def latest_post(self):

        submissions = getattr(self.subreddit, self.post_type.name)(limit = 1)

        for submission in submissions:
            post = submission

        if len(self.url_history) >= self.history_limit:
            self.url_history = self.url_history[-(self.history_limit-1):]

        if post.url in self.url_history:
            return None

        self.url_history.append(post.url)
        self.save(only = [Subreddit.url_history])

        return post

    def get_post_embed(self, post):
        embed = None

        if post.selftext:
            embed = discord.Embed(description = post.selftext, color = 0x8ec07c)
            embed.set_footer(text = post.subreddit_name_prefixed)
            embed.set_author(name = "".join(post.title[:255]), url = post.shortlink)

        elif (hasattr(post, "post_hint") and post.post_hint == "image") or post.url[-3:] in ("jpg","png") or post.url.startswith("https://imgur.com/a"):
            if post.url.startswith("https://imgur.com/a"):
                post.url = post.url + ".jpg"

            embed = discord.Embed(color=0x8ec07c)
            embed.set_image(url = post.url)
            embed.set_footer(text = post.subreddit_name_prefixed)
            embed.set_author(name = "".join(post.title[:255]), url = post.shortlink)

        return embed