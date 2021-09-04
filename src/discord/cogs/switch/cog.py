import discord
from discord.ext import commands

from src.discord.cogs.core import BaseCog
from .settings import FriendCodeSetting

class SwitchCog(BaseCog, name = "Switch"):

    @commands.command()
    async def friendcode(self, ctx):
        friend_code = await FriendCodeSetting.wait(ctx)
        if friend_code is not None:
            friend_code.save()
            await ctx.send("Friend code has been saved.")

def setup(bot):
    bot.add_cog(SwitchCog(bot))