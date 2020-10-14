import discord
import asyncio

from .ui import UI
from src.games.game.base import DiscordIdentity

class DiscordUI(UI):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.message = None

    def get_base_embed(self, **kwargs):
        embed = discord.Embed(**kwargs)
        embed.color = self.ctx.guild_color
        embed.set_author(name = self.ctx.translate("slot_machine"), icon_url = "https://cdn.discordapp.com/attachments/744172199770062899/765694715596242964/slot-machine2.png")
        return embed

    async def show_reel(self, emojis, win):

        delay = 0.3

        if self.message is None:
            self.message = await self.ctx.channel.send(embed=self.get_base_embed(description = emojis[0]))
        else:
            await self.message.edit(embed=self.get_base_embed(description = emojis[0]))

        await asyncio.sleep(delay)

        for emoji in emojis:
            await self.message.edit(embed=self.get_base_embed(description = emoji))
            await asyncio.sleep(delay)

        msg = f" {'+' if win > 0 else '-'}${abs(win)}"
        last_embed = self.get_base_embed(description = emojis[-1])
        last_embed.set_footer(text = msg)
        await self.message.edit(embed = last_embed )

        identity = DiscordIdentity(self.ctx.author)
        identity.add_points(win)
