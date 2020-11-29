import asyncio
from enum import Enum

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Subreddit, database
from src.discord.errors.base import SendableException
from src.discord.helpers.converters import EnumConverter
from src.discord.helpers.checks import is_tester

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
            await asyncio.sleep(60 * 60)
            self.feed_sender.start()

    @commands.check_any(is_tester(), commands.has_guild_permissions(administrator = True))
    @commands.group()
    async def reddit(self, ctx):
        pass

    @reddit.command(name = "add", aliases = ["+"])
    async def reddit_add(self, ctx, subreddit : SubredditConverter, post_type : EnumConverter(Subreddit.PostType) = Subreddit.PostType.hot):
        """Adds a subreddit to the database, this will be sent periodically to the specified channel."""
        if Subreddit.select().where(Subreddit.channel_id == ctx.channel.id, Subreddit.subreddit == subreddit).count() > 0:
            raise SendableException(ctx.translate("subreddit_already_added"))

        guild_id = ctx.guild.id if ctx.guild else None
        subreddit = Subreddit.create(
            guild_id   = guild_id,
            channel_id = ctx.channel.id,
            user_id    = ctx.author.id,
            subreddit  = subreddit,
            post_type  = post_type,
            dm         = ctx.guild is None
        )

        await subreddit.send()
        asyncio.gather(ctx.success())

    @reddit.command(name = "remove", aliases = ["-"])
    async def reddit_remove(self, ctx, subreddit : SubredditConverter, post_type : EnumConverter(Subreddit.PostType) = Subreddit.PostType.hot):
        """Removes a subreddit from the database."""
        Subreddit.delete().where(Subreddit.channel_id == ctx.channel.id).where(Subreddit.subreddit == subreddit).execute()
        await ctx.success()

    @tasks.loop(hours = 1)
    async def feed_sender(self):
        for subreddit in Subreddit.select().where(Subreddit.automatic == True).order_by(Subreddit.channel_id.desc()):
            try:
                asyncio.gather(subreddit.send())
            except Exception as e:
                print(subreddit.id, e)
                pass

def setup(bot):
    bot.add_cog(RedditCog(bot))