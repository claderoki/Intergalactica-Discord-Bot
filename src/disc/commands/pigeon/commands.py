import discord

import src.config as config

GUILD = discord.Object(id=761624318291476482)
group = discord.app_commands.Group(name='pigeon', description='...', guild_ids=[GUILD.id])


@group.command(name='feed', description='Feed the pigeon')
async def pigeon_feed(interaction: discord.Interaction):
    print('feeding...')
