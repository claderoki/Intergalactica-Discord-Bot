import re
import datetime

import discord
from discord.ext import commands, tasks

from src.models import Human, database as db
import src.config as config

class Inactive(discord.ext.commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # self.poll.start()
        pass

    def set_active_or_create(self, member):
        if member.bot:
            return

        now = datetime.datetime.now()

        with db:
            human, created = Human.get_or_create_for_member(member)
            if not created:
                human.last_active = now
                human.save()


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild:
            self.set_active_or_create(message.author)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        joined = before.channel is None and after.channel is not None
        if joined:
            self.set_active_or_create(member)

    def iter_inactives(self):
        for human in Human:
            if human.inactive:
                yield human

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def inactives(self, ctx):
        print("--inactives--")
        for human in self.iter_inactives():
            print(human.user_id)

    # @tasks.loop(hours = 5)
    # async def poll(self):
    #     for human in self.iter_inactives():
    #         try:
    #             await human.inactive_action()
    #         except Exception as e:
    #             print(e)



def setup(bot):
    bot.add_cog(Inactive(bot))