import datetime
from dateutil.relativedelta import relativedelta 

import peewee
import discord
import emoji

from .base import BaseModel
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

