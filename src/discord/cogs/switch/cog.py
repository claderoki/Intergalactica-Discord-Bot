import discord
from discord.ext import commands
from src.discord.helpers.waiters.base import Skipped

from src.discord.cogs.core import BaseCog
from .settings import FriendCodeSetting, DreamAddressSetting, CreatorCodeSetting

class SwitchCog(BaseCog, name = "Switch"):

    @commands.group()
    async def switch(self, ctx):
        pass

    @switch.command(name = "setup")
    async def switch_setup(self, ctx):
        for cls in (FriendCodeSetting, DreamAddressSetting, CreatorCodeSetting):
            try:
                setting = await cls.wait(ctx, skippable = True)
            except Skipped:
                setting = None
            if setting is not None:
                setting.save()
                await ctx.send(f"{setting.code.replace('_', ' ').capitalize()} has been saved.")

        await ctx.success("Done setting up your switch profile")

def setup(bot):
    bot.add_cog(SwitchCog(bot))