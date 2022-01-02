import datetime
from dateutil.relativedelta import relativedelta
import asyncio

from discord.ext import commands, tasks 

from src.discord.cogs.core import BaseCog
from .models import BirthdayReminder, Person, Birthday

class BirthdayReminderCog(BaseCog):

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(5)
        self.start_task(self.poller, check = self.bot.production)

    @tasks.loop(hours = 3)
    async def poller(self):
        if self.bot.owner is None:
            return

        now = datetime.datetime.utcnow()

        query = f"""
        SELECT
            `birthday`.*
        FROM `birthday`
            WHERE `birthday`.`id` NOT IN (SELECT `birthday_id` FROM `birthday_reminder` WHERE `birthday_reminder`.`year` = {now.year})
            AND `birthday`.`month` = {now.month}
            AND `birthday`.`day` = {now.day}
        """

        for birthday in Birthday.raw(query):
            name    = PersonHelper.format_name(birthday.person)
            message = BirthdayHelper.get_message(name, birthday)
            try:
                await self.bot.owner.send(message)
            except:
                continue
            BirthdayReminder.create(year = now.year, birthday = birthday)

class PersonHelper:
    @classmethod
    def format_name(cls, person: Person) -> str:
        if person.first_name is None and person.last_name is None:
            return person.nickname
        else:
            values = filter(None, (person.first_name, person.last_name))
            name   = " ".join(values)
            return f"{name} ({person.nickname})"

class BirthdayHelper:
    @classmethod
    def get_message(cls, name: str, birthday: Birthday) -> str:
        if birthday.year is not None:
            date_of_birth = datetime.datetime(birthday.year, birthday.month, birthday.day)
            age           = relativedelta(datetime.datetime.utcnow(), date_of_birth).years
            return f"{name} has turned {age} today."
        else:
            return f"{name} has increased in age today."


def setup(bot):
    bot.add_cog(BirthdayReminderCog(bot))
