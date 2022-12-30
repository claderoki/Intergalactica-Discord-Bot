from discord.ext import commands

from src.discord import SendableException
from src.discord.cogs.core import BaseCog
from src.discord.helpers import BoolWaiter
from .helpers import *


async def delete_anything(obj):
    try:
        await obj.delete()
    except Exception as e:
        print(e)


class GuildMigrationCog(BaseCog, name="Migration"):
    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def migrate(self, ctx: commands.Context, from_guild_id: int):
        from_guild = self.bot.get_guild(from_guild_id)
        to_guild = ctx.guild

        if from_guild is None:
            raise SendableException("Not in that one.")

        if from_guild == to_guild:
            raise SendableException("?")

        waiter = BoolWaiter(ctx,
                            prompt="Are you should you want to do this? WARNING: THIS WILL COPY A SERVER OVER COMPLETELY")
        if not await waiter.wait():
            raise SendableException("Cancelled.")

        migration = GuildMigration(from_guild, to_guild, ctx.channel)
        await migration.migrate()

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def migrate_emojis(self, ctx: commands.Context, from_guild_id: int):
        from_guild = self.bot.get_guild(from_guild_id)
        to_guild = ctx.guild

        if from_guild is None:
            raise SendableException("Not in that one.")

        if from_guild == to_guild:
            raise SendableException("?")

        waiter = BoolWaiter(ctx,
                            prompt="Are you should you want to do this? WARNING: THIS WILL COPY EMOJIS OVER COMPLETELY")
        if not await waiter.wait():
            raise SendableException("Cancelled.")

        already_added = []
        for emoji in to_guild.emojis:
            already_added.append(emoji.name)

        async with ctx.channel.typing():
            count = 0
            for emoji in from_guild.emojis:
                if emoji.name in already_added:
                    continue
                if count >= 20:
                    break

                raw = requests.get(emoji.url, stream=True).raw.read()
                await to_guild.create_custom_emoji(name=emoji.name, image=raw)

                count += 1

        await ctx.success("OK")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def wipedown(self, ctx: commands.Context):
        waiter = BoolWaiter(ctx,
                            prompt="Are you should you want to do this? WARNING: THIS WILL REMOVE WIPE YOUR SERVER ALMOST COMPLETELY")
        if not await waiter.wait():
            raise SendableException("Cancelled.")

        async with ctx.channel.typing():
            for role in ctx.guild.roles:
                await delete_anything(role)

            for channel in ctx.guild.channels:
                if channel.id == ctx.channel.id:
                    continue
                await delete_anything(channel)

            # for emoji in ctx.guild.emojis:
            #     await self.delete_anything(emoji)

            await ctx.success("Done")


async def setup(bot):
    await bot.add_cog(GuildMigrationCog(bot))
