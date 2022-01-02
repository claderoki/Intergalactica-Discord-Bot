
from discord.ext import tasks, commands

from .helpers.bump_reminder import DisboardBumpReminder
from src.discord.cogs.core import BaseCog
from src.discord.helpers.known_guilds import KnownGuild

class BumpReminders(BaseCog):

    @commands.Cog.listener()
    async def on_message(self, message):
        if DisboardBumpReminder.is_eligible(message):
            await DisboardBumpReminder.recheck_minutes(message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.bump_poller, check = self.bot.production)

    @tasks.loop(minutes = 3)
    async def bump_poller(self):
        for bump_context in DisboardBumpReminder.get_available_bumps():
            content = f"A bump is available! `{DisboardBumpReminder._cmd}` to bump."
            if bump_context.role_id is not None:
                content = f"<@&{bump_context.role_id}>, {content}"
            channel = self.bot.get_channel(bump_context.channel_id)
            if channel is None:
                continue

            last_message = channel.last_message
            if last_message is None or last_message.content != content:
                await channel.send(content)

def setup(bot):
    bot.add_cog(BumpReminders(bot))
