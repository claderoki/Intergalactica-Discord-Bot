from src.discord.cogs.core import BaseCog

from discord.ext import commands, tasks
import asyncio

import src.config as config
from src.discord.helpers.files import FileHelper

class Camera:
    async def capture(self, filepath):
        pass

class PiCamera(Camera):

    def __init__(self):
        import picamera
        self.inst = picamera.PiCamera()

    async def capture(self, filepath):
        self.inst.start_preview()
        self.inst.capture(filepath)
        self.inst.stop_preview()

class LaptopCamera(Camera):
    async def capture(self, filepath):
        import cv2
        cam = cv2.VideoCapture(0)
        cam.read()
        await asyncio.sleep(1)
        frame = cam.read()[1]
        cv2.imwrite(filepath, frame)
        cam.release()

camera_class = PiCamera if True else LaptopCamera

class Personal(BaseCog):
    _started = True
    _camera = camera_class()

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.loop)

    @tasks.loop(seconds = 20)
    async def loop(self):
        if not self._started:
            return

        full_path = f"{config.path}/tmp/frame.png"
        await self._camera.capture(full_path)
        await FileHelper.store(full_path, "frame.png", channel_id=966213030062989334)

    @commands.is_owner()
    @commands.command(name = "cam")
    async def camera_toggle(self, ctx):
        self._started = not self._started
        await ctx.send("OK, camera is now " + str(self._started))

def setup(bot):
    bot.add_cog(Personal(bot))
