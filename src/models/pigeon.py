import datetime
from enum import Enum
import math
import random

from countryinfo import CountryInfo
import peewee

from .base import BaseModel, EnumField, PercentageField, CountryField, LanguageField
from .human import Human, Item, HumanItem
from src.utils.enums import Gender

class Activity(BaseModel):
    start_date = peewee.DateTimeField   (null = True, default = lambda : datetime.datetime.utcnow())
    end_date   = peewee.DateTimeField   (null = True)
    finished   = peewee.BooleanField    (null = False, default = False)

    @property
    def end_date_passed(self):
        return datetime.datetime.utcnow() >= self.end_date

    @property
    def duration_in_minutes(self):
        return int((self.end_date - self.start_date).total_seconds() / 60.0)

class TravelActivity(Activity):
    residence   = CountryField (null = True)
    destination = CountryField (null = True)

    @property
    def distance_in_km(self):
        if self.residence is None or self.destination is None:
            return

        R = 6373.0

        lat1, lon1 = [math.radians(x) for x in self.residence.capital_latlng()]
        lat2, lon2 = [math.radians(x) for x in self.destination.capital_latlng()]

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_duration(self):
        min_time_in_minutes = 30
        max_time_in_minutes = 180
        km = self.distance_in_km
        if km is None:
            return random.randint(min_time_in_minutes, max_time_in_minutes+1)

        duration = int(km / 40)
        if duration < min_time_in_minutes:
            duration = min_time_in_minutes
        elif duration > max_time_in_minutes:
            duration = max_time_in_minutes
        return duration

class Pigeon(BaseModel):
    emojis = {
        "name"        : "📛",
        "gold"        : "",
        "experience"  : "📊",
        "cleanliness" : "💩",
        "food"        : "🌾",
        "happiness"   : "🌻",
        "health"      : "❤️",
    }

    class Status(Enum):
        idle      = "💤"
        mailing   = "📧"
        exploring = "🗺️"
        fighting  = "⚔️"

    class Condition(Enum):
        active   = 1
        ran_away = 2
        dead     = 3

    name                = peewee.TextField       (null = False)
    human               = peewee.ForeignKeyField (Human, backref = "pigeons")
    condition           = EnumField              (Condition, default = Condition.active)
    condition_notified  = peewee.BooleanField    (null = False, default = False)
    experience          = peewee.IntegerField    (null = False, default = 0)
    cleanliness         = PercentageField        (null = False, default = 100)
    happiness           = PercentageField        (null = False, default = 100)
    food                = PercentageField        (null = False, default = 100)
    health              = PercentageField        (null = False, default = 100)
    status              = EnumField              (Status, default = Status.idle)
    gender              = EnumField              (Gender, default = Gender.other)

    def study_language(self, language, mastery = 1):
        language, _ = LanguageMastery.get_or_create(pigeon = self, language = language)
        language.mastery += 1
        language.save()

    def update_stats(self, data):
        for key, value in data.items():
            if key == "gold":
                self.human.gold += value
            else:
                setattr(self, key, (getattr(self, key) + value) )
                if key == "health":
                    if self.health <= 0:
                        self.condition = self.Condition.dead
                        SystemMessage.create(text = "Oh no! Your pigeon has died. Better take better care of it next time!", human = self.human)
        self.save()
        self.human.save()

    @property
    def current_activity(self):
        if self.status == self.Status.exploring:
            return self.explorations.where(Exploration.finished == False).first()
        if self.status == self.Status.mailing:
            return self.outbox.where(Mail.finished == False).first()
        if self.status == self.Status.fighting:
            return self.fights.where(Fight.finished == False).first()

    @property
    def fights(self):
        query = Fight.select()
        query = query.where((Fight.challenger == self) | (Fight.challengee == self))
        return query

class LanguageMastery(BaseModel):
    language = LanguageField()
    mastery  = PercentageField(null = False, default = 0)
    pigeon   = peewee.ForeignKeyField (Pigeon, null = False, backref = "languages", on_delete = "CASCADE")

class SystemMessage(BaseModel):
    human = peewee.ForeignKeyField (Human, null = False, backref = "system_messages", on_delete = "CASCADE")
    text  = peewee.TextField(null = False)
    read  = peewee.BooleanField(null = False, default = False)

    @property
    def embed(self):
        return discord.Embed(description = self.text)

class Mail(TravelActivity):
    recipient   = peewee.ForeignKeyField (Human, null = False, backref = "inbox", on_delete = "CASCADE")
    sender      = peewee.ForeignKeyField (Pigeon, null = False, backref = "outbox", on_delete = "CASCADE")
    gold        = peewee.IntegerField    (null = False, default = 0)
    message     = peewee.TextField       (null = True)
    read        = peewee.BooleanField    (null = False, default = True)

class Exploration(TravelActivity):
    name         = peewee.TextField       (null = True)
    pigeon       = peewee.ForeignKeyField (Pigeon, null = False, backref = "explorations", on_delete = "CASCADE")

    @property
    def xp_worth(self):
        return math.ceil(self.duration_in_minutes)

    @property
    def gold_worth(self):
        return math.ceil(self.duration_in_minutes * 0.8)

class Fight(Activity):
    challenger = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    challengee = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    created_at = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())
    guild_id   = peewee.BigIntegerField (null = False)
    bet        = peewee.BigIntegerField (null = False, default = 50)
    accepted   = peewee.BooleanField    (null = True) # null is pending, true is accepted, false is declined.
    won        = peewee.BooleanField    (null = True) # null is not ended yet, true means challenger won, false means challengee won
