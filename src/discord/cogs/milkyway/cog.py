from discord.ext import commands

from src.discord.cogs.core import BaseCog
from src.models import MilkywaySettings
from .helpers import MilkywayHelper


class MilkywayCog(BaseCog, name="Milkyway"):

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.group()
    async def milkyway(self, ctx):
        pass

    @milkyway.command(name="setup")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def milkyway_setup(self, ctx):
        settings = MilkywaySettings.get_or_none(guild_id=ctx.guild.id)
        new = settings is None

        if new:
            settings = MilkywaySettings(guild_id=ctx.guild.id)

        await settings.editor_for(ctx, "cost_per_day")
        await settings.editor_for(ctx, "category_id")
        await settings.editor_for(ctx, "log_channel_id")
        await settings.editor_for(ctx, "godmode")

        settings.save()

    @milkyway.command(name="create")
    @commands.guild_only()
    async def milkyway_create(self, ctx):
        await MilkywayHelper.create_milkyway(ctx, False)

    @milkyway.command(name="godmode")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def milkyway_godmode(self, ctx):
        await MilkywayHelper.create_milkyway(ctx, True)


def setup(bot):
    bot.add_cog(MilkywayCog(bot))
