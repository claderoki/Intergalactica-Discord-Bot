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

    @commands.Cog.listener()
    async def on_ready(self):
        self.guilds = [x for x in self.bot.guilds if x.owner_id == self.bronk_id]

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
    async def emoji(self, ctx):
        pass

    @emoji.command(name = "add")
    async def emoji_add(self, ctx, name):
        if len(ctx.message.attachments) == 0:
            raise SendableException(ctx.translate("no_attachments"))
        image = ctx.message.attachments[0]

        available_guilds = [x for x in self.guilds if len(x.emojis) < x.emoji_limit]
        guild = available_guilds[0]
        # guild = ctx.guild
        emoji = await guild.create_custom_emoji(name = name, image = await image.read())
        SavedEmoji.create(name = emoji.name, guild_id = guild.id, emoji_id = emoji.id)
        asyncio.gather(ctx.send(ctx.translate("emoji_created")))

    @emoji.command(name = "remove")
    async def emoji_remove(self, ctx, name):
        try:
            saved_emoji = SavedEmoji.get(name = name)
        except SavedEmoji.DoesNotExist:
            return

        asyncio.gather(ctx.send(ctx.translate("emoji_not_removed_yet_because_not_actually_working")))

def setup(bot):
    bot.add_cog(Admin(bot))