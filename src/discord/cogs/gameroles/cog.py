from typing import Dict

import discord
from discord.ext import tasks, commands

from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers import pretty
from src.models import GameRoleSettings
from .helpers import GameRoleProcessor, GameRoleRepository


class GameRoleCog(BaseCog, name="Game role"):
    processors: Dict[int, GameRoleProcessor] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for settings in GameRoleRepository.get_all_settings():
            self.processors[settings.guild_id] = GameRoleProcessor(settings)

        self.start_task(self.clean_all)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # if not self.bot.production:
        #     return

        if after.bot:
            return

        processor = self.processors.get(before.guild.id)
        if processor is None:
            return

        if after.activities != before.activities:
            for activity in after.activities:
                if activity.type == discord.ActivityType.playing:
                    await processor.process(after, activity)

    @commands.command()
    @commands.guild_only()
    async def games(self, ctx):
        data = []
        for game_role in GameRoleRepository.get_all_for_guild(ctx.guild.id):
            role = ctx.guild.get_role(game_role.role_id)
            if role is not None:
                data.append((game_role.game_name, len(role.members)))
        data.sort(key=lambda x: x[1], reverse=True)

        data.insert(0, ("name", "members"))
        table = pretty.Table.from_list(data, first_header=True)
        await table.to_paginator(ctx, 10).wait()

    @commands.command()
    @commands.guild_only()
    async def game(self, ctx, *, name: str):
        processor = self.processors.get(ctx.guild.id)
        if processor is None:
            raise SendableException("Not setup for this server.")

        data = [("member",)]

        role = processor.get_role(name)
        if role is None:
            raise SendableException("Role not found.")

        for member in role.members:
            data.append((str(member),))

        table = pretty.Table.from_list(data, first_header=True)
        await table.to_paginator(ctx, 10).wait()

    @commands.group()
    @commands.guild_only()
    async def gameroles(self, ctx):
        pass

    @gameroles.command(name="toggle")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def gameroles_toggle(self, ctx):
        settings = GameRoleRepository.get_settings(ctx.guild.id)
        if settings is None:
            await self.bot.get_command("gameroles setup")(ctx)
        settings.enabled = not settings.enabled

        if ctx.guild.id in self.processors and not settings.enabled:
            del self.processors[ctx.guild.id]
        elif settings.enabled:
            self.processors[ctx.guild.id] = GameRoleProcessor(settings)

        settings.save()
        await ctx.success(f"Game role is now {'enabled' if settings.enabled else 'disabled'} for this server")

    @gameroles.command(name="setup")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def gameroles_setup(self, ctx):
        processor = self.processors.get(ctx.guild.id)
        if processor is not None:
            settings = processor.settings
        else:
            settings = GameRoleSettings(guild_id=ctx.guild.id)

        await settings.editor_for(ctx, "threshhold", min=1, max=10)
        await settings.editor_for(ctx, "log_channel_id", skippable=True)
        settings.save()
        await ctx.success("Setup.")

        if processor is None:
            self.processors[ctx.guild.id] = GameRoleProcessor(settings)

    @tasks.loop(minutes=60)
    async def clean_all(self):
        for processor in self.processors.values():
            await processor.cleanup()


def setup(bot):
    bot.add_cog(GameRoleCog(bot))
