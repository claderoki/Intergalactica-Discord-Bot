from discord.ext import commands, tasks

from src.disc.cogs.core import BaseCog
from src.models import MilkywaySettings, Milkyway
from .helpers import MilkywayHelper, MilkywayProcessor, MilkywayUI, MilkywayCache, MilkywayRepository
from ... import SendableException


class MilkywayCog(BaseCog, name="Milkyway"):

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.delete_expired_channels, check=self.bot.production)

    # @commands.group()
    # @commands.guild_only()
    # async def milkyway(self, ctx):
    #     pass

    # @milkyway.command(name="setup")
    # @commands.has_permissions(administrator=True)
    # async def milkyway_setup(self, ctx):
    #     settings = MilkywayCache.get_settings(ctx.guild.id)
    #     if settings is None:
    #         settings = MilkywaySettings(guild_id=ctx.guild.id)

    #     await settings.editor_for(ctx, "cost_per_day")
    #     await settings.editor_for(ctx, "category_id")
    #     await settings.editor_for(ctx, "log_channel_id")
    #     await settings.editor_for(ctx, "active_limit")
    #     await settings.editor_for(ctx, "godmode")

    #     settings.save()
    #     await ctx.success("OK")

    # @milkyway.command(name="create")
    # async def milkyway_create(self, ctx):
    #     processor = MilkywayProcessor(ctx, False)
    #     milkyway = await processor.create()
    #     request_channel = ctx.guild.get_channel(processor.settings.log_channel_id)
    #     await request_channel.send(embed=MilkywayUI.get_pending_embed(milkyway))
    #     await ctx.success("Your milkyway has been requested.")

    # @milkyway.command(name="godmode")
    # @commands.has_permissions(administrator=True)
    # async def milkyway_godmode(self, ctx):
    #     processor = MilkywayProcessor(ctx, True)
    #     milkyway = await processor.create()
    #     await MilkywayHelper.accept(milkyway)

    # @milkyway.command(name="extend")
    # async def milkyway_extend(self, ctx, id: int):
    #     milkyway = Milkyway.get(identifier=id, guild_id=ctx.guild.id)
    #     if milkyway.status != Milkyway.Status.accepted:
    #         raise SendableException(f"This milk is already `{milkyway.status}`")

    #     processor = MilkywayProcessor(ctx, milkyway.purchase_type == Milkyway.PurchaseType.none)
    #     await processor.extend(milkyway)
    #     await milkyway.channel.edit(topic=MilkywayHelper.get_channel_topic(milkyway))

    #     await ctx.success("Your milkyway has been extended.")

    # @milkyway.command(name="accept")
    # @commands.has_guild_permissions(administrator=True)
    # async def milkyway_accept(self, ctx, id: int):
    #     milkyway = Milkyway.get(identifier=id, guild_id=ctx.guild.id)
    #     if milkyway.status != Milkyway.Status.pending:
    #         raise SendableException(f"This milk is already `{milkyway.status}`")

    #     await MilkywayHelper.accept(milkyway)
    #     await ctx.success()
    #     await milkyway.member.send("Your milkyway has been accepted.")

    # @milkyway.command(name="deny")
    # @commands.has_guild_permissions(administrator=True)
    # async def milkyway_deny(self, ctx, id: int, *, reason: str):
    #     if not reason:
    #         raise SendableException("Reason is mandatory.")

    #     milkyway = Milkyway.get(identifier=id, guild_id=ctx.guild.id)
    #     if milkyway.status != Milkyway.Status.pending:
    #         raise SendableException(f"This milk is already `{milkyway.status}`")

    #     await MilkywayHelper.deny(milkyway, reason)
    #     await ctx.success("Successfully denied.")
    #     await milkyway.member.send(embed=MilkywayUI.get_denied_embed(milkyway))

    @tasks.loop(minutes=60)
    async def delete_expired_channels(self):
        for milkyway in MilkywayRepository.get_expired():
            await MilkywayHelper.expire(milkyway)


async def setup(bot):
    await bot.add_cog(MilkywayCog(bot))
