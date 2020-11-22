import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Subreddit, database
from src.discord.errors.base import SendableException

class SubredditConverter(commands.Converter):
    @classmethod
    async def convert(cls, ctx, argument):
        return config.bot.reddit.subreddit(argument)

class RedditCog(commands.Cog, name = "Reddit"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.feed_sender.start()

    @commands.has_guild_permissions(administrator = True)
    @commands.group()
    async def reddit(self, ctx):
        pass

    @reddit.command(name = "add", aliases = ["+"])
    async def reddit_add(self, ctx, subreddit : SubredditConverter):
        """Adds a subreddit to the database, this will be sent periodically to the specified channel."""
        if Subreddit.select().where(Subreddit.channel_id == ctx.channel.id, Subreddit.subreddit == subreddit).count() > 0:
            raise SendableException(ctx.translate("subreddit_already_added"))

        sr = Subreddit.create(guild_id = ctx.guild.id, channel_id = ctx.channel.id, subreddit = subreddit)
        await sr.send()

    @reddit.command(name = "remove", aliases = ["-"])
    async def reddit_remove(self, ctx, subreddit : SubredditConverter):
        """Removes a subreddit from the database."""
        Subreddit.delete().where(Subreddit.channel_id == ctx.channel.id).where(Subreddit.subreddit == subreddit).execute()
        await ctx.success()

    @tasks.loop(hours = 1)
    async def feed_sender(self):
        for subreddit in Subreddit.select().order_by(Subreddit.guild_id.desc()):
            await subreddit.send()

def setup(bot):
    bot.add_cog(RedditCog(bot))