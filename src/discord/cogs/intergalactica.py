import asyncio

import discord
from discord.ext import commands

class Intergalactica(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(742146159711092757)

    def member_is_legal(self, member):
        age_roles       = [748606669902053387,748606823229030500,748606893387153448,748606902363095206]
        gender_roles    = [742301620062388226, 742301646004027472, 742301672918745141]

        has_age_role = False
        has_gender_role = False

        for role in member.roles:
            if role.id in age_roles:
                has_age_role = True
            elif role.id in gender_roles:
                has_gender_role = True

        return has_age_role and has_gender_role

    def illegal_member_iterator(self):
        for member in self.guild.members:
            if member.bot:
                continue

            if not self.member_is_legal(member):
                yield member

    @commands.command()
    async def mandatorycheck(self, ctx):
        embed = discord.Embed(color = ctx.guild_color, title = "Members without mandatory roles")

        lines = []
        for member in self.illegal_member_iterator():
            lines.append(member.mention)

        embed.description = "\n".join(lines)

        await ctx.send(embed = embed)

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def purgeintros(self, ctx):
        channel = ctx.guild.get_channel(742567349613232249)

        coros = []
        async for message in channel.history(limit=200):
            if not isinstance(message.author, discord.Member):
                embed = discord.Embed(
                    color = ctx.guild_color,
                    title = f"Introduction by {message.author}",
                    description = message.content)
                coros.append( ctx.send(embed = embed) )

                await message.delete()

        if len(coros) == 0:
            embed = discord.Embed(title ="Nothing to purge.", color = ctx.guild_color)
            coros.append( ctx.send(embed = embed) )

        asyncio.gather(*coros)


    @commands.command()
    @commands.dm_only()
    async def concern(self, ctx, *, concern):
        guild = self.guild
        channel = guild.get_channel(758296826549108746)

        embed = discord.Embed(color = self.bot.get_dominant_color(guild) )
        embed.set_author(name = "Anonymous concern", icon_url=guild.icon_url)
        embed.description = concern
        await channel.send(embed = embed)





def setup(bot):
    bot.add_cog(Intergalactica(bot))