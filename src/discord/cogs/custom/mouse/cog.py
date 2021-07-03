

from discord.ext import commands
import praw

from src.discord.cogs.custom.shared.cog import CustomCog
import src.config as config

class Mouse(CustomCog):
    guild_id = 729843647347949638

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
