from discord.ext import commands

from src.discord.cogs.custom.shared.cog import CustomCog
from src.discord.helpers.known_guilds import KnownGuild


class KnownRole:
    underage = 919621466016862218


class Guac(CustomCog):
    guild_id = KnownGuild.guac

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id == self.guild_id:
            for role in after.roles:
                if role.id == KnownRole.underage:
                    await after.ban(reason="Underage role")


async def setup(bot):
    await bot.add_cog(Guac(bot))
