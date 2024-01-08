from discord.ext import commands

from src.disc.cogs.custom.shared.cog import CustomCog
from src.disc.helpers.known_guilds import KnownGuild


class KnownRole:
    underage = 1116864734159970416


class Hut(CustomCog):
    guild_id = KnownGuild.hut

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id == self.guild_id:
            for role in after.roles:
                if role.id == KnownRole.underage:
                    await after.ban(reason="Underage role")


async def setup(bot):
    await bot.add_cog(Hut(bot))
