import re
import datetime

import discord
from discord.ext import commands, tasks

from src.models import Human, database as db
import src.config as config
from src.discord.helpers.waiters import BoolWaiter

class Inactive(discord.ext.commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    def set_active_or_create(self, member):
        if member.bot:
            return

        with db:
            human, created = Human.get_or_create_for_member(member)
            if not created:
                human.last_active = datetime.datetime.utcnow()
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

        inactive_members = []
        for human in self.iter_inactives(ctx.guild):
            if human.member.premium_since is None:
                inactive_members.append(human.member)
                lines.append( str(human.member) )

        embed.description = "\n".join(lines)
        await ctx.send(embed = embed)

        waiter = BoolWaiter(ctx, prompt = "Kick?")
        to_kick = await waiter.wait()
        if to_kick:
            for member in inactive_members:
                await member.kick(reason = "Inactivity")


    # @tasks.loop(hours = 5)
    # async def poll(self):
    #     for human in self.iter_inactives():
    #         try:
    #             await human.inactive_action()
    #         except Exception as e:
    #             print(e)



def setup(bot):
    bot.add_cog(Inactive(bot))