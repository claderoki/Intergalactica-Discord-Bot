import re
import datetime

import discord
from discord.ext import commands, tasks

from src.models import Earthling, database
import src.config as config
from src.discord.helpers.waiters import BoolWaiter
from src.discord.cogs.core import BaseCog

class Inactive(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    def set_active_or_create(self, member):
        if member.bot:
            return

        with database.connection_context():
            earthling, created = Earthling.get_or_create_for_member(member)
            if not created:
                earthling.last_active = datetime.datetime.utcnow()
                earthling.save()

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
        for earthling in Earthling.select().where(Earthling.guild_id == guild.id):
            if earthling.guild is None or earthling.member is None:
                continue
            if earthling.inactive and not earthling.member.bot:
                yield earthling

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def inactives(self, ctx):
        embed = discord.Embed(title = "Inactives", color = ctx.guild_color )
        lines = []

        inactive_members = []
        for earthling in self.iter_inactives(ctx.guild):
            if earthling.member.premium_since is None:
                inactive_members.append(earthling.member)
                lines.append( str(earthling.member) )

        embed.description = "\n".join(lines)
        await ctx.send(embed = embed)

        if len(inactive_members) > 0:
            waiter = BoolWaiter(ctx, prompt = "Kick?")
            to_kick = await waiter.wait()
            if to_kick:
                for member in inactive_members:
                    await member.kick(reason = "Inactivity")

def setup(bot):
    bot.add_cog(Inactive(bot))