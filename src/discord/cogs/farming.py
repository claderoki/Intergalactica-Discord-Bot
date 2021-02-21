import random
import asyncio
import datetime

import requests
import discord
from discord.ext import commands

import src.config as config
from src.discord.cogs.core import BaseCog
from src.models import Farm, Crop, Human, FarmCrop
from src.discord.helpers.converters import StringConverter
from src.discord.errors.base import SendableException

class FarmingCog(BaseCog, name = "Farming"):

    def __init__(self, bot):
        super().__init__(bot)

    def get_farm_crop_query(self, farm, crop_name = None, finished = False, due = False):
        query = FarmCrop.select()
        query = query.where(FarmCrop.finished == finished)
        query = query.join(Crop)
        if crop_name is not None:
            query = query.where(Crop.name == crop_name)
        query = query.where(FarmCrop.farm == farm)
        if due:
            query = query.where(FarmCrop.due_date <= datetime.datetime.utcnow())
        return query

    @commands.group(name = "farm")
    async def farm(self, ctx):
        ctx.farm, _ = Farm.get_or_create(human = ctx.get_human())

    @farm.command(name = "view")
    async def farm_view(self, ctx):
        farm_crop = self.get_farm_crop_query(ctx.farm).first()
        if farm_crop is None:
            raise SendableException(ctx.translate("nothing_planted"))

        stage = farm_crop.current_stage
        image_path = farm_crop.crop.get_stage_sprite_path(stage)

        embed = discord.Embed(color = discord.Color.green())

        image = await self.bot.store_file(image_path, filename = "file.png")
        embed.set_image(url = image)
        embed.set_footer(text = f"Stage {stage} / {Crop.max_stages}")

        await ctx.send(embed = embed)

    @farm.command(name = "plant")
    async def farm_plant(self, ctx, crop_name : StringConverter(Crop.pluck("name"))):
        farm_crop = self.get_farm_crop_query(ctx.farm).first()
        if farm_crop is not None:
            raise SendableException(ctx.translate("already_planted"))

        crop = Crop.get(name = crop_name)
        ctx.farm.plant(crop = crop)

        await ctx.success(ctx.translate("crop_planted").format(crop = crop))

    @farm.command(name = "harvest")
    async def farm_harvest(self, ctx):
        farm_crop = self.get_farm_crop_query(ctx.farm, due = True)
        if farm_crop is not None:
            raise SendableException(ctx.translate("nothing_to_harvest"))
        farm_crop.finished = True
        farm_crop.save()

        await ctx.success(ctx.translate("crop_harvested").format(crop = farm_crop.crop))


def setup(bot):
    bot.add_cog(FarmingCog(bot))