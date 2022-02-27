from discord.ext import commands

from src.discord.cogs.core import BaseCog
from src.discord.helpers.known_guilds import KnownGuild
from .helpers import WelcomeMessage


class WelcomeCog(BaseCog):
    _welcome_message_configs = {}

    def add_guild(self, guild_id: int, channel_id: int, message: str):
        channel = self.bot.get_channel(channel_id)
        if channel is None or channel.guild.id != guild_id:
            return
        self._welcome_message_configs[guild_id] = WelcomeMessage(guild_id, channel, message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.add_guild(KnownGuild.kail, 884843718534901864,
                       "Welcome {member.mention}! make sure to get <#884851898346254356> and <#884851962212929547>!")
        self.add_guild(KnownGuild.mio, 902296733588029534, "{member.mention} just joined us! Happy to see you!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        if not self.bot.production:
            return

        welcome_config = self._welcome_message_configs.get(message.guild.id)
        if welcome_config is not None:
            if welcome_config.is_welcoming_message(message):
                await welcome_config.react(message)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        if not self.bot.production:
            return

        welcome_config = self._welcome_message_configs.get(member.guild.id)
        if welcome_config is not None:
            await welcome_config.send(member)


def setup(bot):
    bot.add_cog(WelcomeCog(bot))
