from math import perm
from sympy import per
import discord
from discord.ext import commands

from src.discord.helpers import ColorHelper
from src.discord.helpers.known_guilds import KnownGuild
from ..shared.cog import CustomCog


class KnownChannel:
    conspiracy = 905587705537265695
    keith = 952992095747063888


class KnownRole:
    conspiracy_redirector = 953731354158305340


class KnownEmoji:
    ians_face = 852909058276458496


class MessageRedirector:
    __slots__ = ("trigger_emoji", "channel_id", "permission_role")

    def __init__(self, trigger_emoji, channel_id: int, permission_role: int):
        self.trigger_emoji = trigger_emoji
        self.channel_id = channel_id
        self.permission_role = permission_role


class Cam(CustomCog):
    guild_id = KnownGuild.cam
    redirectors = {}

    def add_message_redirector(self, message_redirector: MessageRedirector):
        self.redirectors[message_redirector.trigger_emoji] = message_redirector

    @commands.Cog.listener()
    async def on_ready(self):
        self.add_message_redirector(MessageRedirector(KnownEmoji.ians_face, KnownChannel.conspiracy, KnownRole.conspiracy_redirector))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # if self.bot.production:
        #     return

        if payload.guild_id != self.guild_id:
            return

        emoji = str(payload.emoji) if payload.emoji.id is None else payload.emoji.id
        redirector: MessageRedirector = self.redirectors.get(emoji)

        if emoji is None or redirector is None:
            return

        if payload.channel_id == redirector.channel_id:
            return

        guild = self.bot.get_guild(self.guild_id)
        member = guild.get_member(payload.user_id)

        if redirector.permission_role not in [x.id for x in member.roles]:
            return

        from_channel = guild.get_channel(payload.channel_id)
        message = await from_channel.fetch_message(payload.message_id)

        channel = member.guild.get_channel(redirector.channel_id)
        await message.delete()

        content = message.content if is_video(message.content) else None

        embed = message_to_embed(message)
        embed.set_footer(text=f"Redirected by {member} ({member.id})")
        await channel.send(content, embed=embed)


def is_video(content: str) -> bool:
    return "youtube" in content or "youtu.be" in content

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
