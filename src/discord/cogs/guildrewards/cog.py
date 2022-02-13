import discord
from discord.ext import commands

from src.discord.cogs.core import BaseCog
from .helpers import *


class GuildRewardsCog(BaseCog, name="Server Rewards"):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.bot.production:
            return
        if message.guild is None or message.author.bot:
            return

        settings = GuildRewardsCache.get_settings(message.guild.id)
        if settings is None or not settings.enabled:
            return

        profile = GuildRewardsCache.get_profile(message.guild.id, message.author.id)
        if GuildRewardsHelper.has_reward_available(profile, settings):
            GuildRewardsHelper.reward(profile, settings)

    @commands.group()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def rewards(self, ctx):
        pass

    @rewards.command(name="setup")
    async def rewards_setup(self, ctx):
        settings = GuildRewardsCache.get_settings(ctx.guild.id)
        if settings is None:
            settings = GuildRewardsSettings(guild_id=ctx.guild.id)

        await settings.editor_for(ctx, "timeout")
        await settings.editor_for(ctx, "min_points_per_message")
        await settings.editor_for(ctx, "max_points_per_message")
        settings.save()
        await ctx.success("Done setting up.")


def setup(bot):
    bot.add_cog(GuildRewardsCog(bot))
