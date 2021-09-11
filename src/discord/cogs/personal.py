
import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
from src.discord.cogs.core import BaseCog

def is_permitted():
    def predicate(ctx):
        authorized = ctx.author.id in (ctx.bot.owner.id, ctx.cog.user_id)
        return authorized and (ctx.guild is None or ctx.guild.member_count < 10)
    return commands.check(predicate)

class Personal(BaseCog):
    @commands.Cog.listener()
    async def on_ready(self):
        pass

def setup(bot):
    bot.add_cog(Personal(bot))
