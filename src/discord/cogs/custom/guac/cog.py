import discord

from discord.ext import commands

from src.discord.helpers.known_guilds import KnownGuild
from src.discord.cogs.custom.shared.cog import CustomCog
import src.config as config

class KnownChannel:
    pass

class KnownRole:
    underage = 919621466016862218

class Guac(CustomCog):
    guild_id = KnownGuild.guac

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        for role in after.roles:
            if role.id == KnownRole.underage:
                await after.ban(reason = "Underage role")

def setup(bot):
    bot.add_cog(Guac(bot))
