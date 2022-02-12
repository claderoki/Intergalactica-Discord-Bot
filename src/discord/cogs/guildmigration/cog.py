from discord.ext import commands

from src.discord.cogs.core import BaseCog
from .helpers import *
from src.discord import SendableException
from src.discord.helpers import BoolWaiter

class GuildMigrationCog(BaseCog, name = "Migration"):
    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    # @commands.has_guild_permissions(administrator = True)
    async def migrate(self, ctx: commands.Context, from_guild_id: int):
        from_guild = self.bot.get_guild(from_guild_id)
        to_guild   = ctx.guild

        if from_guild is None:
            raise SendableException("Not in that one.")

        if from_guild == to_guild:
            raise SendableException("?")

        waiter = BoolWaiter(ctx, prompt = "Are you should you want to do this? WARNING: THIS WILL COPY A SERVER OVER COMPLETELY")
        if not await waiter.wait():
            raise SendableException("Cancelled.")

        migration = GuildMigration(from_guild, to_guild, ctx.channel)
        await migration.migrate()

    async def delete_anything(self, obj):
        try:
            await obj.delete()
        except Exception as e:
            print(e)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def wipedown(self, ctx: commands.Context):
        waiter = BoolWaiter(ctx, prompt = "Are you should you want to do this? WARNING: THIS WILL REMOVE WIPE YOUR SERVER ALMOST COMPLETELY")
        if not await waiter.wait():
            raise SendableException("Cancelled.")

        async with ctx.channel.typing():
            for role in ctx.guild.roles:
                await self.delete_anything(role)

            for channel in ctx.guild.channels:
                if channel.id == ctx.channel.id:
                    continue
                await self.delete_anything(channel)

            # for emoji in ctx.guild.emojis:
            #     await self.delete_anything(emoji)

            await ctx.success("Done")

def setup(bot):
    bot.add_cog(GuildMigrationCog(bot))
