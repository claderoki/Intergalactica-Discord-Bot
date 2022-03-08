import asyncio
from discord.ext import commands

from src.discord.cogs.core import BaseCog
from src.discord.helpers.known_guilds import KnownGuild
from .helpers import WelcomeMessage


class WelcomeCog(BaseCog):
    _welcome_message_configs = {}
    _instant_leavers = set()

    def add_guild(self, guild_id: int, channel_id: int, message: str):
        channel = self.bot.get_channel(channel_id)
        if channel is None or channel.guild.id != guild_id:
            return
        self._welcome_message_configs[guild_id] = WelcomeMessage(guild_id, channel, message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.add_guild(KnownGuild.kail, 884843718534901864, "Welcome {member.mention}! make sure to get <#884851898346254356> and <#884851962212929547>!")
        self.add_guild(KnownGuild.mio, 942170622132387860, "{member.mention} just joined us! Happy to see you!")
        self.add_guild(KnownGuild.mouse, 729909438378541116, "Welcome to the server {member.mention}, <@&841072184953012275> say hello!")

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
            if member.guild.id == KnownGuild.mouse:
                await asyncio.sleep(60)
            if member.id not in self._instant_leavers:
                await welcome_config.send(member)
                self._instant_leavers.remove(member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            return

        if not self.bot.production:
            return

        welcome_config = self._welcome_message_configs.get(member.guild.id)
        if welcome_config is not None:
            self._instant_leavers.add(member.id)
            await welcome_config.remove(member)


def setup(bot):
    bot.add_cog(WelcomeCog(bot))
