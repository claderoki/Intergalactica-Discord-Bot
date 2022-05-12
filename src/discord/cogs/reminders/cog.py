import datetime
import discord
from discord.ext import tasks, commands

from src.discord.helpers.colors import ColorHelper
from src.discord.cogs.core import BaseCog
from src.models import Reminder

class RemindersCog(BaseCog, name="Reminder"):
    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.loop, check=self.bot.production)

    @tasks.loop(seconds = 60)
    async def loop(self):
        for reminder in Reminder.select().where(Reminder.sent == False).where(Reminder.due_date >= datetime.datetime.utcnow()):
            sendable = reminder.channel
            embed = discord.Embed(color=ColorHelper.get_dominant_color(), description=reminder.message)
            await sendable.send(f"<@{reminder.user_id}>", embed=embed)
            reminder.sent = True
            reminder.save()

def setup(bot):
    bot.add_cog(RemindersCog(bot))
