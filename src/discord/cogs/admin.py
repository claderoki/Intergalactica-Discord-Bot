import asyncio

import discord
from discord.ext import commands

import src.config as config
from src.models import SavedEmoji, Human, database
from src.discord.errors.base import SendableException

class Admin(discord.ext.commands.Cog):
    bronk_id = 771781840012705792

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.is_owner()
    @commands.group()
    async def tester(self, ctx):
        pass

    @tester.command(name = "add", aliases = ["=", "+"])
    async def add_tester(self, ctx, member : discord.Member):
        human, _ = Human.get_or_create(user_id = member.id)
        human.tester = True
        human.save()
        asyncio.gather(ctx.success())

    @tester.command(name = "remove", aliases = ["-", "del"])
    async def remove_tester(self, ctx, member : discord.Member):
        human, _ = Human.get_or_create(user_id = member.id)
        human.tester = False
        human.save()
        asyncio.gather(ctx.success())

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