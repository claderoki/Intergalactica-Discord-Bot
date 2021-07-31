import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum

import peewee
import discord
import emoji
import pycountry

from .base import BaseModel, EnumField, CountryField
from src.utils.timezone import Timezone
import src.config as config
from src.utils.zodiac import ZodiacSign

class CurrenciesField(peewee.TextField):
    def db_value(self, value):
        if value:
            return ";".join(set(x.alpha_3 for x in value if x is not None))

    def python_value(self, value):
        if value:
            return set(pycountry.currencies.get(alpha_3 = x) for x in value.split(";"))
        else:
            return set()

class Human(BaseModel):
    user_id               = peewee.BigIntegerField  (null = False, unique = True)
    gold                  = peewee.BigIntegerField  (null = False, default = 250)
    timezone              = peewee.TextField        (null = True)
    date_of_birth         = peewee.DateField        (null = True)
    city                  = peewee.TextField        (null = True)
    country               = CountryField            (null = True, column_name = "country_code")
    tester                = peewee.BooleanField     (null = False, default = False)
    currencies            = CurrenciesField         (null = False, default = lambda : set())

    class Meta:
        indexes = (
            (('user_id',), True),
        )

    @property
    def all_currencies(self):
        currencies = set()
        if self.country:
            for currency in self.country.currencies():
                currencies.add(currency)
        if self.currencies is not None:
            for currency in self.currencies:
                currencies.add(currency)
        return set(x for x in currencies if x is not None)

    @property
    def mention(self):
        return f"<@{self.user_id}>"

    @property
    def pigeon(self):
        for pigeon in self.pigeons:
            if pigeon.condition == pigeon.Condition.active:
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

    def calculate_timezone(self):
        if self.city is not None and self.country is not None:
            city = self.bot.owm_api.by_q(self.city, self.country.alpha_2)
            if city is not None:
                return str(city.timezone)

        elif self.country is not None:
            if self.country.alpha_2 not in ("US", "CA"):
                latlng = self.country.capital_latlng()
                timezone = Timezone.from_location(*latlng[::-1])
                if timezone is not None:
                    return timezone.name

    def add_item(self, item, amount = 1, found = False):
        human_item, created = HumanItem.get_or_create(item = item, human = self)
        if created:
            human_item.amount = amount
        else:
            human_item.amount += amount

        if found:
            human_item.found = True
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

    @property
    def zodiac_sign(self):
        if self.date_of_birth is not None:
            return ZodiacSign.from_date(self.date_of_birth)

    def get_embed_field(self, show_all = False):
        #TODO: clean up.
        name = self.user.name
        # if show_all and self.country:
            # name += f" {self.country.flag_emoji}"
        values = []

        if self.date_of_birth is not None:
            days_until_birthday = self.days_until_birthday
            age = self.age
            value = f"{self.zodiac_sign.emoji} {age}"
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

        if self.pigeon is not None:
            values.append("<:pigeon:767362416941203456> " + self.pigeon.name)
        elif show_all:
            values.append("<:pigeon:767362416941203456> N/A")

        if self.city is not None:
            city = self.bot.owm_api.by_q(self.city, self.country.alpha_2 if self.country else None)
            if city is not None:
                emoji = city.weather_infos[0].emoji
                temp = city.temperature_info.temperature
                symbol = city.unit.symbol
                cog = config.bot.cogs["Conversion"]
                unit = cog.unit_mapping.get_unit("c")
                result = cog.base_measurement_to_conversion_result(unit, temp)

                value = f"{emoji} {temp}{symbol}"
                for to in result.to:
                    value += f" / {to.get_clean_string()}"

                values.append(value)

        elif show_all:
            values.append("🌡️ N/A")

        if self.gold is not None:
            values.append(f"{self.bot.gold_emoji} {self.gold}")
        elif show_all:
            values.append(f"{self.bot.gold_emoji} N/A")

        if len(values) == 0:
            values.append("N/A")

        sep  = "\n"
        if not show_all:
            sep += "\n"

        return {"name" : name, "value" : sep.join(values), "inline" : True}

class ItemCategory(BaseModel):
    name   = peewee.CharField       (null = False)
    code   = peewee.CharField       (max_length = 45)
    parent = peewee.ForeignKeyField ("self", null = True)

class Item(BaseModel):
    class Rarity(Enum):
        junk      = 1
        common    = 2
        uncommon  = 3
        rare      = 4
        legendary = 5

        @property
        def color(self):
            if self == self.junk:
                return discord.Color.from_rgb(168, 115, 77)
            elif self == self.common:
                return discord.Color.from_rgb(196, 100, 70)
            elif self == self.uncommon:
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
            elif self == self.uncommon:
                return 20
            elif self == self.rare:
                return 10
            elif self == self.legendary:
                return 6

    name         = peewee.CharField       (null = False)
    code         = peewee.CharField       (max_length = 45)
    description  = peewee.TextField       (null = False)
    image_url    = peewee.TextField       (null = False)
    rarity       = EnumField              (Rarity, null = False, default = Rarity.common)
    explorable   = peewee.BooleanField    (null = False, default = False)
    usable       = peewee.BooleanField    (null = False, default = False)
    category     = peewee.ForeignKeyField (ItemCategory, null = True)
    chance       = peewee.IntegerField    (null = False)

    @classmethod
    def get_random(cls):
        query = """
            SELECT results.* FROM (
            SELECT {table_name}.*, @running_total AS previous_total, @running_total := @running_total + {chance_column_name} AS running_total, until.rand
            FROM (
                SELECT round(rand() * init.max) AS rand FROM (
                SELECT sum({chance_column_name}) - 1 AS max FROM {table_name} {where}
                ) AS init
            ) AS until,
            (SELECT * FROM {table_name} {where}) AS {table_name},
            ( SELECT @running_total := 0.00 ) AS vars
            ) AS results
            WHERE results.rand >= results.previous_total AND results.rand < results.running_total;
        """

        query = query.format(
            table_name = cls._meta.table_name,
            where = "WHERE (category_id != 1 OR category_id IS NULL) AND explorable = 1",
            chance_column_name = "chance"
        )

        for item in cls.raw(query):
            return item

    @property
    def embed(self):
        embed = discord.Embed(color = self.rarity.color)
        embed.set_thumbnail(url = self.image_url)
        embed.title = self.name
        embed.description = self.description
        return embed

class HumanItem(BaseModel):
    human  = peewee.ForeignKeyField (Human, null = False, backref = "human_items")
    item   = peewee.ForeignKeyField (Item, null = False)
    amount = peewee.IntegerField    (null = False, default = 1)
    found  = peewee.BooleanField    (null = False, default = False)

    class Meta:
        indexes = (
            (("human", "item"), True),
        )
