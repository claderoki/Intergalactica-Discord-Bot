import discord
from discord.ext import commands

from src.discord.helpers.pretty import Table
from src.discord.cogs.core import BaseCog
from .helpers import *
from src.discord import SendableException

class InactiveChannelsCog(BaseCog, name = "Inactive channels"):

    @commands.group(aliases = ["ic"])
    async def inactivechannels(self, ctx):
        pass

    @inactivechannels.command(name = "setup")
    @commands.guild_only()
    async def inactivechannels_setup(self, ctx):
        settings = InactiveChannelsRepository.get_settings(ctx.guild.id)
        if settings is None:
            settings = InactiveChannelsSettings(guild_id = ctx.guild.id)

        await settings.editor_for(ctx, "timespan")
        await settings.editor_for(ctx, "max_messages")
        settings.save()

        await ctx.success("Done setting up.")

    @inactivechannels.command(name = "check")
    @commands.guild_only()
    async def inactivechannels_check(self, ctx: commands.Context):
        settings = InactiveChannelsRepository.get_settings(ctx.guild.id)
        if settings is None:
            raise SendableException("Not setup yet.")

        await ctx.trigger_typing()
        inactive_channels = []
        for channel in ctx.guild.text_channels:
            inactive = await InactiveChannelsHelper.is_inactive(channel, settings)
            if inactive:
                inactive_channels.append(channel)

        await ctx.send("\n".join(map(str, inactive_channels)))

def setup(bot):
    bot.add_cog(InactiveChannelsCog(bot))
