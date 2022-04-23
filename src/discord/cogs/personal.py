from src.discord.cogs.core import BaseCog
import cv2

from discord.ext import commands, tasks
import asyncio
import src.config as config
from src.discord.helpers.files import FileHelper

class Personal(BaseCog):
    _started = True

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.loop)

    @tasks.loop(seconds = 20)
    async def loop(self):
        cam = cv2.VideoCapture(0)
        frame = cam.read()[1]
        await asyncio.sleep(5)
        frame = cam.read()[1]
        full_path = f"{config.path}/tmp/frame.png"
        cv2.imwrite(full_path, frame)
        cam.release()
        await FileHelper.store(full_path, "frame.png", channel_id=966213030062989334)

    @commands.is_owner()
    async def camera_toggle(self, ctx):
        self._started = not self._started
        await ctx.send("OK, camera is now " + str(self._started))

def setup(bot):
    bot.add_cog(Personal(bot))
