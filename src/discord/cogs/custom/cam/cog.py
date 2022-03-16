import discord
from discord.ext import commands

from src.discord.helpers import ColorHelper
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
        if self.bot.production:
            return

        if isinstance(reaction.emoji, str):
            return

        if reaction.emoji.id != KnownEmoji.ians_face:
            return

        if KnownRole.conspiracy_redirector not in [x.id for x in member.roles]:
            return

        message = reaction.message
        if message.channel.id == KnownChannel.conspiracy:
            return

        channel = member.guild.get_channel(KnownChannel.conspiracy)
        await message.delete()

        content = message.content if "youtube" in message.content else None
        await channel.send(content, embed=message_to_embed(message))


def message_to_embed(message: discord.Message) -> discord.Embed:
    embed = discord.Embed(color=ColorHelper.get_primary_color())
    embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
    embed.description = message.content
    if "http" in message.content and ("png" in message.content or "jpg" in message.content):
        embed.set_image(url=message.content)
    else:
        for attachment in message.attachments:
            embed.set_image(url=attachment.url)
            break

    return embed


def setup(bot):
    bot.add_cog(Cam(bot))
