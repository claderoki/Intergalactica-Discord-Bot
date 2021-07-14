import asyncio

from discord.ext import commands
import praw

from src.discord.cogs.custom.shared.cog import CustomCog
import src.config as config

class Mouse(CustomCog):
    guild_id = 729843647347949638

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.guild.id != self.guild_id:
            return

        await super().on_message(message)

        if AnimalCrossingBotHelper.is_not_allowed(message):
            await AnimalCrossingBotHelper.warn(message)

    @commands.Cog.listener()
    async def on_ready(self):
        await super().on_ready()
        self.praw_instances[self.guild_id] = praw.Reddit(
            client_id       = config.environ["mouse_reddit_client_id"],
            client_secret   = config.environ["mouse_reddit_client_secret"],
            user_agent      = config.environ["mouse_reddit_user_agent"],
            username        = config.environ["mouse_reddit_username"],
            password        = config.environ["mouse_reddit_password"],
            check_for_async = False
        )
 
def setup(bot):
    bot.add_cog(Mouse(bot))

class AnimalCrossingBotHelper:
    bot_id = 701038771776520222

    __slots__ = ()

    @classmethod
    def is_not_allowed(cls, message):
        return message.channel.id == 763146096766877697 and message.content and message.content.lower().startswith("ac!profile set")

    @classmethod
    async def warn(cls, message):
        try:
            bot_response = await config.bot.wait_for("message", check = lambda x : x.author.id == cls.bot_id and x.channel.id == message.channel.id, timeout = 60)
        except asyncio.TimeoutError:
            bot_response = None
        if bot_response is not None:
            await bot_response.delete()
        await message.channel.send(f"{message.author.mention}, please use this command in <#768529385161752669>", delete_after = 30)
        await message.delete()
