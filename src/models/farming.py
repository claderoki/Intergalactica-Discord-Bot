import datetime
import math

import peewee
from dateutil.relativedelta import relativedelta
from src.config import config
from .base import BaseModel, TimeDeltaField
from . import Human, Item


class Farm(BaseModel):
    human = peewee.ForeignKeyField(Human)

    def plant(self, crop):
        return FarmCrop.create(
            crop=crop,
            farm=self,
            due_date=datetime.datetime.utcnow() + crop.grow_time
        )


class Crop(BaseModel):
    max_stages = 4

    name = peewee.CharField(null=False)
    code = peewee.CharField(null=False)
    grow_time = TimeDeltaField(null=False, default=datetime.timedelta(hours=12))

    # range     = RangeField             (null = False, default = lambda : range(2, 6))

    @property
    def root_path(self):
        return f"{config.path}/resources/sprites/farming"

    @property
    def seed_item(self):
        return Item.get(code=f"{self.name.lower()}_seed")

    @property
    def product_item(self):
        return Item.get(code=f"{self.name.lower()}_product")

    def get_seed_sprite_path(self):
        return f"{self.root_path}/{self.name.title()}/{self.name.lower()}_seed.png"

    def get_product_sprite_path(self):
        return f"{self.root_path}/{self.name.title()}/{self.name.lower()}_product.png"

    def get_stage_sprite_path(self, stage):
        stage = max(min(stage, self.max_stages), 1)
        return f"{self.root_path}/{self.name.title()}/{self.name.lower()}_stage_{stage}.png"

    @classmethod
    async def convert(cls, ctx, argument):
        return cls.get(name=argument)


class FarmCrop(BaseModel):
    planted_at = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())
    farm = peewee.ForeignKeyField(Farm, null=False)
    crop = peewee.ForeignKeyField(Crop, null=False)
    finished = peewee.BooleanField(null=False, default=False)
    due_date = peewee.DateTimeField(null=False)

    @property
    def percentage_grown(self):
        pass

    @property
    def current_stage(self):
        grow_time = self.crop.grow_time
        hours_per_stage = (grow_time.seconds / 3600) / Crop.max_stages

        difference = relativedelta(datetime.datetime.utcnow(), self.planted_at)
        hours = difference.hours + (difference.days * 24)

        stage = math.ceil(hours / hours_per_stage)
        return max(min(stage, Crop.max_stages), 1)
