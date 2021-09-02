from discord.ext import tasks, commands

from src.discord.cogs.custom.shared.cog import CustomCog

class Intergalactica(CustomCog):
    guild_id = 742146159711092757

    @commands.Cog.listener()
    async def on_ready(self):
        self.praw_instances[self.guild_id] = self.bot.reddit
        # await super().on_ready()

def setup(bot):
    bot.add_cog(Intergalactica(bot))
