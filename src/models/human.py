import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum

import peewee
import discord
import emoji

from .base import BaseModel, EnumField
from src.utils.timezone import Timezone
import src.config as config

emojize = lambda x : emoji.emojize(x, use_aliases=True)

class Human(BaseModel):
    user_id               = peewee.BigIntegerField  (null = False, unique = True)
    gold                  = peewee.BigIntegerField  (null = False, default = 250)
    timezone              = peewee.TextField        (null = True)
    date_of_birth         = peewee.DateField        (null = True)
    city                  = peewee.TextField        (null = True)
    country_code          = peewee.TextField        (null = True)
    tester                = peewee.BooleanField     (null = False, default = False)

    class Meta:
        indexes = (
            (('user_id',), True),
        )

    @property
    def mention(self):
        return f"<@{self.user_id}>"

    @property
    def pigeon(self):
        for pigeon in self.pigeons:
            if not pigeon.dead:
                return pigeon

    @property
    def current_time(self):
        if self.timezone is not None:
            return Timezone(self.timezone).current_time

    @property
    def age_delta(self):
        if self.date_of_birth is not None:
            return relativedelta(datetime.datetime.utcnow(), self.date_of_birth)

    @property
    def age(self):
        if self.date_of_birth is not None:
            return self.age_delta.years

    @property
    def birthday(self):
        if self.date_of_birth is None:
            return False

        current_date = datetime.datetime.utcnow()
        return self.date_of_birth.day == current_date.day and self.date_of_birth.month == current_date.month

    def add_item(self, item, amount):
        human_item, created = HumanItem.get_or_create(item = item, human = self)
        if created:
            human_item.amount = amount
        else:
            human_item.amount += amount
        human_item.save()
        return human_item

    @property
    def next_birthday(self):
        if self.date_of_birth is None:
            return None

        current_date = datetime.datetime.utcnow()

        if current_date.month >= self.date_of_birth.month and current_date.day >= self.date_of_birth.day:
            return datetime.datetime(current_date.year + 1, self.date_of_birth.month, self.date_of_birth.day)
        else:
            return datetime.datetime(current_date.year, self.date_of_birth.month, self.date_of_birth.day)

    @property
    def minutes_until_birthday(self):
        return abs((datetime.datetime.utcnow() - self.next_birthday).minutes)

    @property
    def days_until_birthday(self):
        return abs((datetime.datetime.utcnow() - self.next_birthday).days)

    def get_embed_field(self, show_all = False):

        name = self.user.name
        values = []

        if self.date_of_birth is not None:
            days_until_birthday = self.days_until_birthday
            age = self.age
            value = f"🎂 {self.age}"
            if days_until_birthday < 10:
                value += f" (days left: {days_until_birthday})"
            values.append(value)
        elif show_all:
            values.append("🎂 N/A")

        if self.timezone is not None:
            timezone = Timezone(self.timezone)
            time = str(timezone.current_time.strftime('%H:%M'))
            values.append(f"🕑 {time}")
        elif show_all:
            values.append("🕑 N/A")

        if self.country_code:
            flag = "".join([emojize(f":regional_indicator_symbol_letter_{x}:") for x in self.country_code.lower()])
            name += " " + flag

        if self.pigeon is not None:
            values.append("<:pigeon:767362416941203456> " + self.pigeon.name)
        elif show_all:
            values.append("<:pigeon:767362416941203456> N/A")

        if self.city is not None:
            city = self.bot.owm_api.by_q(self.city, self.country_code)
            values.append(f"{city.weather_infos[0].emoji} {city.temperature_info.temperature}{city.unit.symbol}")
        elif show_all:
            values.append("🌡️ N/A")

        if self.gold is not None:
            values.append(f"{self.bot.gold_emoji} {self.gold}")
        elif show_all:
            values.append(f"{self.bot.gold_emoji} N/A")

        if len(values) == 0:
            values.append("N/A")

        return {"name" : name, "value" : "\n".join(values), "inline" : True}


class Item(BaseModel):
    class Rarity(Enum):
        junk      = 1
        common    = 2
        rare      = 3
        legendary = 4

        @property
        def color(self):
            if self == self.junk:
                return discord.Color.from_rgb(168, 115, 77)
            elif self == self.common:
                return discord.Color.from_rgb(196, 100, 70)
            elif self == self.rare:
                return discord.Color.from_rgb(196, 100, 70)
            elif self == self.legendary:
                return discord.Color.from_rgb(196, 100, 70)

        @property
        def weight(self):
            if self == self.junk:
                return 40
            elif self == self.common:
                return 30
            elif self == self.rare:
                return 20
            elif self == self.legendary:
                return 10

    name        = peewee.CharField    (null = False)
    description = peewee.TextField    (null = False)
    image_url   = peewee.TextField    (null = False)
    rarity      = EnumField           (Rarity, null = False, default = Rarity.common)
    explorable  = peewee.BooleanField (null = False, default = False)

    @property
    def embed(self):
        embed = discord.Embed()
        # embed.color = self.bot.calculate_dominant_color(self.image_url)
        embed.set_thumbnail(url = self.image_url)
        embed.title = self.name
        embed.description = self.description
        return embed

class HumanItem(BaseModel):
    human  = peewee.ForeignKeyField (Human, null = False)
    item   = peewee.ForeignKeyField (Item, null = False)
    amount = peewee.IntegerField    (null = False, default = 1)

    class Meta:
        indexes = (
            (("human", "item"), True),
        )
