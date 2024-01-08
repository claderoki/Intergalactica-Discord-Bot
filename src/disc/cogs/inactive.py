import datetime

import discord
from discord.ext import commands

import src.config as config
from src.disc.cogs.core import BaseCog
from src.disc.helpers.known_guilds import KnownGuild
from src.disc.helpers.waiters import BoolWaiter
from src.models import Earthling, database


class Inactive(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    def set_active_or_create(self, member):
        if member.bot:
            return

        with database.connection_context():
            now = datetime.datetime.utcnow()
            query = Earthling.update(last_active=now)
            query = query.where(Earthling.user_id == member.id)
            query = query.where(Earthling.guild_id == member.guild.id)
            rows_affected = query.execute()

            if rows_affected == 0:
                try:
                    Earthling.insert(
                        guild_id=member.guild.id,
                        user_id=member.id,
                        human=config.bot.get_human(user=member)
                    )
                except Exception as e:
                    print(e)
                    pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return

        if message.guild:
            self.set_active_or_create(message.author)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.bot.production:
            return

        joined = before.channel is None and after.channel is not None
        if joined:
            self.set_active_or_create(member)

    def iter_inactives(self, guild):
        query = Earthling.select(Earthling.guild_id, Earthling.user_id, Earthling.last_active)
        for earthling in query.where(Earthling.guild_id == guild.id):
            if earthling.guild is None or earthling.member is None:
                continue
            if earthling.inactive:
                if earthling.guild_id == KnownGuild.mouse:
                    if 852955124967276556 not in [x.id for x in earthling.member.roles]:
                        yield earthling
                else:
                    yield earthling

    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.command()
    @commands.guild_only()
    async def inactives(self, ctx):
        embed = discord.Embed(title="Inactives", color=ctx.guild_color)
        lines = []

        inactive_members = []
        for earthling in self.iter_inactives(ctx.guild):
            if earthling.member.premium_since is None or ctx.guild.id == KnownGuild.intergalactica:
                inactive_members.append(earthling.member)
                lines.append(str(earthling.member))

        if len(inactive_members) == 0:
            return await ctx.error("NO INACTIVES TO BE DESTROYED")

        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

        waiter = BoolWaiter(ctx, prompt="Kick?")
        to_kick = await waiter.wait()
        if to_kick:
            for member in inactive_members:
                await member.kick(reason="Inactivity")
            await ctx.success("Done destroying inactives.")
        else:
            await ctx.success("Canceled the destruction of the inactives.")


async def setup(bot):
    await bot.add_cog(Inactive(bot))
