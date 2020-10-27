import datetime
from enum import Enum
import math

from countryinfo import CountryInfo
import peewee

from .base import BaseModel, EnumField
from .human import Human

class PercentageField(peewee.IntegerField):
    def db_value(self, value):
        if value is not None:
            return max(min(value, 100), 0)

    # def python_value(self, value):
    #     if value is not None:
    #         return self.enum[value]


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
    residence    = peewee.TextField       (null = True)
    destination  = peewee.TextField       (null = True)

    @property
    def distance_in_km(self):
        if self.residence is None or self.destination is None:
            return

        R = 6373.0

        lat1, lon1 = [math.radians(x) for x in CountryInfo(self.residence).capital_latlng()]
        lat2, lon2 = [math.radians(x) for x in CountryInfo(self.destination).capital_latlng()]

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_duration(self):
        min_time_in_minutes = 30
        max_time_in_minutes = 180

        duration = int(self.distance_in_km / 40)
        if duration < min_time_in_minutes:
            duration = min_time_in_minutes
        elif duration > max_time_in_minutes:
            duration = max_time_in_minutes
        return duration

class Pigeon(BaseModel):
    emojis = {
        "gold"        : "",
        "experience"  : "📊",
        "cleanliness" : "💩",
        "food"        : "🌾",
        "happiness"   : "🌻",
        "health"      : "❤️"
    }

    class Status(Enum):
        idle      = "💤"
        mailing   = "📧"
        exploring = "🗺️"
        fighting  = "⚔️"

    name          = peewee.TextField       (null = False)
    human         = peewee.ForeignKeyField (Human, backref = "pigeons")
    dead          = peewee.BooleanField    (null = False, default = False)
    experience    = peewee.IntegerField    (null = False, default = 0)
    cleanliness   = PercentageField        (null = False, default = 100)
    happiness     = PercentageField        (null = False, default = 100)
    food          = PercentageField        (null = False, default = 100)
    health        = PercentageField        (null = False, default = 100)
    status        = EnumField              (Status, default = Status.idle)

    @property
    def current_activity(self):
        if self.status == self.Status.exploring:
            return self.explorations.where(Exploration.finished == False).first()
        if self.status == self.Status.mailing:
            return self.outbox.where(Mail.finished == False).first()
        if self.status == self.Status.fighting:
            query = Fight.select()
            query = query.where(Fight.finnished == False)
            query = query.where((Fight.challenger == self) | (Fight.challengee == self))
            return query.first()

    class Meta:
        table_name = "new_pigeon"

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
    accepted   = peewee.BooleanField    (null = True) # null is pending, true is accepted, false is declined.
    won        = peewee.BooleanField    (null = True) # null is not ended yet, true means challenger won, false means challengee won
