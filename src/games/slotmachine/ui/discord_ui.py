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

    async def show_reel(self, fruits, win):
        delay = 0.3
        empty = "🔲"
        # empty = "🔳"

        count = 4
        for i in range(count):
            emojis = [x.emoji for x in fruits[:i]]
            for _ in range(count - (i+1)):
                emojis.append(empty)

            embed = self.get_base_embed(description = "".join(emojis))
            if i == (count-1):
                msg = f" {'+' if win > 0 else '-'}{abs(win)}"
                embed.set_footer(text = msg)
            if self.message is None:
                self.message = await self.ctx.channel.send(embed = embed)
            else:
                await self.message.edit(embed = embed)
            await asyncio.sleep(delay)

        identity = DiscordIdentity(self.ctx.author)
        identity.add_points(win)
