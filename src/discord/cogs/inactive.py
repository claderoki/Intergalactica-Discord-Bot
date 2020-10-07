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

        return
        humans = {}
        for human in Human.select().where(Human.guild_id == 742146159711092757):
            if human.user_id not in humans:
                humans[human.user_id] = []

            humans[human.user_id].append(human)

        for user_id, _humans in humans.items():
            if len(_humans) > 1:
                human1 = _humans[0]
                human2 = _humans[1]

                if human1.last_active == None and human2.last_active == None:
                    human1.delete_instance()
                    continue

                if human1.last_active != None and human2.last_active == None:
                    human2.delete_instance()
                    continue

                if human1.last_active == None and human2.last_active != None:
                    human1.delete_instance()
                    continue

                if human1.last_active > human2.last_active:
                    print("to delete human 2")
                    human2.delete_instance()

                elif human2.last_active > human1.last_active:
                    print("to delete human 1")
                    human1.delete_instance()

                print(user_id)

    def set_active_or_create(self, member):
        if member.bot:
            return

        now = datetime.datetime.utcnow()

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

    def iter_inactives(self, guild):
        for human in Human.select().where(Human.guild_id == guild.id):
            if human.guild is None or human.member is None:
                continue
            if human.inactive and not human.member.bot:
                yield human

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def inactives(self, ctx):
        embed = discord.Embed(title = "Inactives", color = ctx.guild_color )
        lines = []
        for human in self.iter_inactives(ctx.guild):
            if human.member.premium_since is None:
                lines.append( str(human.member) )

        embed.description = "\n".join(lines)
        await ctx.send(embed = embed)


    # @tasks.loop(hours = 5)
    # async def poll(self):
    #     for human in self.iter_inactives():
    #         try:
    #             await human.inactive_action()
    #         except Exception as e:
    #             print(e)



def setup(bot):
    bot.add_cog(Inactive(bot))