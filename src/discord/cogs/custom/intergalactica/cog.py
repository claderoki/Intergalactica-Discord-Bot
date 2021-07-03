from discord.ext import tasks, commands

from src.discord.cogs.custom.shared.cog import CustomCog
import src.config as config

class Intergalactica(CustomCog):
    guild_id = 742146159711092757

    commands.Cog.listener()
    async def on_ready(self):
        await super().on_ready()
        self.praw_instances[self.guild_id] = config.reddit

def setup(bot):
    bot.add_cog(Intergalactica(bot))
