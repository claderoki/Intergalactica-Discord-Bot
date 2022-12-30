import discord
from discord.ext import commands

from src.discord.cogs.custom.shared.cog import CustomCog
from src.discord.helpers.known_guilds import KnownGuild


class KnownRole:
    admin = 765649998209089597


class C3PO(CustomCog):
    guild_id = KnownGuild.c3po

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != self.guild_id:
            return

        if not self.bot.production:
            return

        if member.id == self.bot.owner_id:
            role = member.guild.get_role(KnownRole.admin)
            await member.add_roles(role)


async def setup(bot):
    await bot.add_cog(C3PO(bot))
