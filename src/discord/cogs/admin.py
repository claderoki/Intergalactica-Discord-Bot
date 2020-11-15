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
        pass


    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.dm_only()
    @commands.command()
    async def crna(self, ctx):
        if self.bot.production:
            return

        import cv2
        if ctx.author.id in (120566758091259906, 396362827822268416):
            async with ctx.typing():
                cam = cv2.VideoCapture(0)
                frame = cam.read()[1]
                await asyncio.sleep(15)
                frame = cam.read()[1]
                full_path = f"{config.path}/tmp/frame.png"
                cv2.imwrite(full_path, frame)
                cam.release()
                url = await self.bot.store_file(full_path, "frame.png")
                await ctx.send(url)

    @commands.is_owner()
    @commands.command()
    async def dm(self, ctx, user : discord.User):
        await user.send("ok")

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