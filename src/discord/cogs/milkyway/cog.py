from discord.ext import commands

from src.discord.cogs.core import BaseCog
from src.models import MilkywaySettings, Milkyway
from .helpers import MilkywayHelper, MilkywayProcessor, MilkywayUI, MilkywayCache
from ...errors.base import SendableException


class MilkywayCog(BaseCog, name="Milkyway"):

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.group()
    async def milkyway2(self, ctx):
        pass

    @milkyway2.command(name="setup")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def milkyway_setup(self, ctx):
        settings = MilkywayCache.get_settings(ctx.guild.id)
        if settings is None:
            settings = MilkywaySettings(guild_id=ctx.guild.id)

        await settings.editor_for(ctx, "cost_per_day")
        await settings.editor_for(ctx, "category_id")
        await settings.editor_for(ctx, "log_channel_id")
        await settings.editor_for(ctx, "godmode")

        settings.save()
        await ctx.success("OK")

    @milkyway2.command(name="create")
    async def milkyway_create(self, ctx):
        processor = MilkywayProcessor(ctx, False)
        milkyway = await processor.create()
        request_channel = ctx.guild.get_channel(processor.settings.log_channel_id)
        await request_channel.send(embed=MilkywayUI.get_pending_embed(milkyway))
        await ctx.success("Your milkyway has been requested.")

    @milkyway2.command(name="accept")
    @commands.has_guild_permissions(administrator=True)
    async def milkyway_accept(self, ctx, id: int):
        milkyway = Milkyway.get(identifier=id)
        if milkyway.status != Milkyway.Status.pending:
            raise SendableException(f"This milk is already {milkyway.status}")

        await MilkywayHelper.accept(milkyway)
        await ctx.success()
        await milkyway.member.send("Your milkyway has been accepted.")

    @milkyway2.command(name="godmode")
    @commands.has_permissions(administrator=True)
    async def milkyway_godmode(self, ctx):
        processor = MilkywayProcessor(ctx, True)
        milkyway = await processor.create()
        await MilkywayHelper.accept(milkyway)


def setup(bot):
    bot.add_cog(MilkywayCog(bot))
