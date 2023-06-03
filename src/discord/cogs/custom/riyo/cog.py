import csv
import io

import requests
from discord.ext import commands, tasks

from src.discord.cogs.custom.shared.cog import CustomCog

TARGET_NAME = "Demon Commie"


def get_difference(a, b):
    return int(((a - b) * 100) / a)


class UserRank:
    __slots__ = ('rank', 'username', 'gained')

    def __init__(self, rank: int, username: str, gained: int):
        self.rank = rank
        self.username = username
        self.gained = gained


class Riyo(CustomCog):
    guild_id = 1114046141638656000
    gen_channel_id = 1114046141638656003

    def __init__(self, bot):
        super().__init__(bot)
        self.previous_difference = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)
        self.start_task(self.loop, True)
        self.mention = '<@119191078900465667>'

    async def notify(self, message):
        channel = self.guild.get_channel(self.gen_channel_id)
        await channel.send(message)

    @tasks.loop(minutes=1)
    async def loop(self):
        first = self.previous_difference is None
        url = 'https://api.wiseoldman.net/v2/competitions/25222/csv?table=participants'
        request = requests.get(url)
        csv_data = io.StringIO(request.text)
        reader = csv.DictReader(csv_data)

        target_index = None
        rankings = []
        for row in reader:
            ranking = UserRank(int(row['Rank']), row['Username'], int(row['Gained']))
            if ranking.username == TARGET_NAME:
                target_index = len(rankings)
            rankings.append(ranking)

        if target_index == 1:
            person_ahead = rankings[target_index - 1]
            target = rankings[target_index]

            difference = get_difference(person_ahead.gained, target.gained)
            if self.previous_difference is None:
                self.previous_difference = difference

            if first or self.previous_difference != difference:
                await self.notify(f'{self.mention}, dude wtf, you\'re losing to {person_ahead.username} by {difference}%')
        elif target_index > 0:
            difference = 99
            if first or self.previous_difference != difference:
                await self.notify(f'{self.mention}, dude wtf, you\'re losing to multiple people!')
        else:
            person_behind = rankings[target_index + 1]
            target = rankings[target_index]

            difference = get_difference(target.gained, person_behind.gained)
            if self.previous_difference is None:
                self.previous_difference = difference

            if difference < self.previous_difference:
                await self.notify(
                    f'Dude wtf, {person_behind.username} is catching up, you were {self.previous_difference}% ahead '
                    f'before, and now only {difference}')
            elif difference != self.previous_difference or first:
                await self.notify(f'You are {difference}% ahead of {person_behind.username}, keep it up champ')

        self.previous_difference = difference


async def setup(bot):
    await bot.add_cog(Riyo(bot))
