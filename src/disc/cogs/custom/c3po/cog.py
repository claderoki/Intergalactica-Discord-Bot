import discord
from discord.ext import commands

from src.disc.cogs.custom.shared.cog import CustomCog
from src.disc.helpers.known_guilds import KnownGuild


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

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.owner = (await self.bot.application_info()).owner
        self.bot.owner_id = self.bot.owner.id

        self.bot._emoji_mapping = {}
        for emoji in self.bot.get_guild(761624318291476482).emojis:
            self.bot._emoji_mapping[emoji.name] = emoji
        if self.bot.restarted:
            await self.bot.owner.send(content="Started up")
            self.bot.restarted = False



async def setup(bot):
    await bot.add_cog(C3PO(bot))
