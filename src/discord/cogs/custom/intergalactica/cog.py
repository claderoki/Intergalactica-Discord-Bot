from discord.ext import tasks, commands

from src.discord.helpers.known_guilds import KnownGuild
from src.discord.cogs.custom.shared.cog import CustomCog
from src.discord.cogs.custom.shared.helpers.praw_cache import PrawInstanceCache

class Intergalactica(CustomCog):
    guild_id = KnownGuild.intergalactica

    @commands.Cog.listener()
    async def on_ready(self):
        pass

def setup(bot):
    bot.add_cog(Intergalactica(bot))
