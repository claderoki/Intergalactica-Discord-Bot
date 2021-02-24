import random
import asyncio
import datetime
import os

import requests
import discord
from discord.ext import commands
from PIL import Image

import src.config as config
from src.discord.cogs.core import BaseCog
from src.models import Farm, Crop, FarmCrop, Human, HumanItem
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
        crop_path = farm_crop.crop.get_stage_sprite_path(stage)
        crop = farm_crop.crop
        embed = discord.Embed(color = discord.Color.green())
        embed.title = f"{crop.name}"
        path = f"{config.path}/tmp/{crop.name.lower()}_stage_{stage}.png"

        if not os.path.exists(path):
            background = Image.open(f"{crop.root_path}/background.png")
            crop = Image.open(crop_path)

            image = Image.new('RGBA',(background.size[0], background.size[1]))
            image.paste(background,(0,0))
            image.paste(crop,(0,0), crop.convert('RGBA'))
            image.save(path, "PNG")

        file = await self.bot.store_file(path, filename = "file.png")
        embed.set_image(url = file)
        embed.set_footer(text = f"Stage {stage} / {Crop.max_stages}")

        await ctx.send(embed = embed)

    @farm.command(name = "plant")
    async def farm_plant(self, ctx, crop_name : StringConverter(Crop.pluck("name"))):
        farm_crop = self.get_farm_crop_query(ctx.farm).first()
        if farm_crop is not None:
            raise SendableException(ctx.translate("already_planted"))

        crop = Crop.get(name = crop_name)
        item = crop.seed_item

        human_item = HumanItem.get_or_none(item = item, human = ctx.get_human())
        if human_item is None or human_item.amount <= 0:
            raise SendableException(ctx.translate("item_not_enough").format(amount = 1))

        ctx.farm.plant(crop = crop)

        human_item.amount -= 1
        human_item.save()

        await ctx.success(ctx.translate("crop_planted").format(crop = crop))

    @farm.command(name = "harvest")
    async def farm_harvest(self, ctx):
        farm_crop = self.get_farm_crop_query(ctx.farm, due = True).first()
        if farm_crop is None:
            raise SendableException(ctx.translate("nothing_to_harvest"))
        farm_crop.finished = True
        farm_crop.save()
        crop = farm_crop.crop
        item = crop.product_item

        human_item, _   = HumanItem.get_or_create(item = item, human = ctx.get_human())
        products_gained = random.randint(2, 6)

        human_item.amount += products_gained
        human_item.save()

        embed = discord.Embed(color = discord.Color.green())
        embed.description = f"You have successfully harvested {products_gained} {item.name}s!"
        embed.set_image(url = item.image_url)
        await ctx.send(embed = embed)

def setup(bot):
    bot.add_cog(FarmingCog(bot))