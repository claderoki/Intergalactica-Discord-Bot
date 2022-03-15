import asyncio
import datetime
import random

import discord
from discord.ext import commands

import src.config as config
from src.discord.helpers.known_guilds import KnownGuild
from ..shared.cog import CustomCog

class KnownChannel:
    conspiracy = 905587705537265695


class KnownRole:
    conspiracy_redirector = 953386405185351721

class KnownEmoji:
    ians_face = 852909058276458496

class Cam(CustomCog):
    guild_id = KnownGuild.cam

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member):
        # if not self.bot.production:
        #     return

        if reaction.emoji.id != KnownEmoji.ians_face:
            return

        if KnownRole.conspiracy_redirector not in [x.id for x in member.roles]:
            return

        if reaction.message.channel.id == KnownChannel.conspiracy:
            return

        channel = member.guild.get_channel(KnownChannel.conspiracy)
        await reaction.message.delete()

        embed = (discord.Embed(description=reaction.message.content)
            .set_author(name = member.name, icon_url = member.avatar_url))

        await channel.send(embed = embed)


def setup(bot):
    bot.add_cog(Cam(bot))
