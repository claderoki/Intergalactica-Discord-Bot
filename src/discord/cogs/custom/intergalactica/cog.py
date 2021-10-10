from discord.ext import tasks, commands

from src.discord.cogs.custom.shared.helpers.bump_reminder import DisboardBumpReminder
from src.discord.helpers.known_guilds import KnownGuild
from src.discord.cogs.custom.shared.cog import CustomCog

class Intergalactica(CustomCog):
    guild_id = KnownGuild.intergalactica

    @commands.Cog.listener()
    async def on_ready(self):
        DisboardBumpReminder.cache(self.guild_id, 742146159711092757)
        self.praw_instances[self.guild_id] = self.bot.reddit

def setup(bot):
    bot.add_cog(Intergalactica(bot))
