import asyncio

import discord
from discord.ext import commands

import src.config as config
from src.models import SavedEmoji, database
from src.discord.errors.base import SendableException

class Admin(discord.ext.commands.Cog):
    bronk_id = 771781840012705792

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        self.guilds = [x for x in self.bot.guilds if x.owner_id == self.bronk_id]

    @commands.group()
    @commands.is_owner()
    async def emoji():
        pass

    @emoji.command()
    @commands.is_owner()
    async def add(self, ctx, name):
        if len(ctx.message.attachments) == 0:
            raise SendableException(ctx.translate("no_attachments"))

        print()

def setup(bot):
    bot.add_cog(Admin(bot))