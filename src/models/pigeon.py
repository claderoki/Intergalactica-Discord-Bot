import datetime
from enum import Enum
import math
import random

from dateutil.relativedelta import relativedelta
import discord
import peewee

from .base import BaseModel, EnumField, PercentageField, TimeDeltaField, CountryField, LanguageField
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
        min_time_in_minutes = 45
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
        dating    = "❤️"

    class Condition(Enum):
        active   = 1
        ran_away = 2
        dead     = 3

    name                = peewee.TextField       (null = False)
    human               = peewee.ForeignKeyField (Human, backref = "pigeons")
    condition           = EnumField              (Condition, default = Condition.active)
    experience          = peewee.IntegerField    (null = False, default = 0)
    cleanliness         = PercentageField        (null = False, default = 100)
    happiness           = PercentageField        (null = False, default = 100)
    food                = PercentageField        (null = False, default = 100)
    health              = PercentageField        (null = False, default = 100)
    status              = EnumField              (Status, default = Status.idle)
    gender              = EnumField              (Gender, default = Gender.other)
    pvp                 = peewee.BooleanField    (null = False, default = False)
    last_used_pvp       = peewee.DateTimeField   (null = True)

    @property
    def can_disable_pvp(self):
        if self.last_used_pvp is None:
            return True

        return (relativedelta(datetime.datetime.utcnow(), self.last_used_pvp).hours > 12)

    def study_language(self, language, mastery = 1):
        language, _ = LanguageMastery.get_or_create(pigeon = self, language = language)
        language.mastery += mastery
        language.save()

    def create_buff(self, code, create_system_message = True):
        buff = Buff.get(code = code)
        pigeon_buff, _ = PigeonBuff.get_or_create(pigeon = self, buff = buff)
        pigeon_buff.due_date = datetime.datetime.utcnow() + buff.duration
        pigeon_buff.save()
        if create_system_message:
            SystemMessage.create(
                text = self.bot.translate("buff_assigned").format(buff = buff),
                human = self.human
            )

    def update_stats(self, data, increment = True, save = True):
        for key, value in data.items():
            if key == "gold":
                self.human.gold += value
            else:
                if increment:
                    setattr(self, key, (getattr(self, key) + value))
                else:
                    setattr(self, key, value)

                # new_value = getattr(self, key)
                # if key == "food" and new_value >= 100:
                    # self.create_buff("fully_fed")

                if key == "health":
                    if self.health <= 0:
                        self.condition = self.Condition.dead
                        SystemMessage.create(text = self.bot.translate("pigeon_dead"), human = self.human)
        try:
            if save:
                self.save()
                self.human.save()
        except ValueError:
            pass

    @property
    def current_activity(self):
        if self.status == self.Status.exploring:
            return self.explorations.where(Exploration.finished == False).first()
        if self.status == self.Status.mailing:
            return self.outbox.where(Mail.finished == False).first()
        if self.status == self.Status.fighting:
            query = Fight.select()
            query = query.where(Fight.finished == False)
            query = query.where((Fight.pigeon1 == self) | (Fight.pigeon2 == self))
            return query.first()
        if self.status == self.Status.dating:
            query = Date.select()
            query = query.where(Date.finished == False)
            query = query.where((Date.pigeon1 == self) | (Date.pigeon2 == self))
            return query.first()

    @property
    def buffs(self):
        return self._buffs.where(PigeonBuff.due_date > datetime.datetime.utcnow())

    @property
    def fights(self):
        query = Fight.select()
        query = query.where((Fight.challenger == self) | (Fight.challengee == self))
        return query

class Buff(BaseModel):
    name        = peewee.TextField       (null = False)
    description = peewee.TextField       (null = False)
    code        = peewee.TextField       (null = False)
    duration    = TimeDeltaField         (null = False)

    # stat        = peewee.TextField       (null = True)
    # type        = EnumField              (Type, default = Type.add)
    # amount      = peewee.IntegerField    (null = False, default = 0)
    # class Type(Enum):
    #     add      = 1
    #     remove   = 2
    #     modifier = 3

class PigeonBuff(BaseModel):
    pigeon      = peewee.ForeignKeyField (Pigeon, null = False, backref = "_buffs", on_delete = "CASCADE")
    buff        = peewee.ForeignKeyField (Buff, null = False, on_delete = "CASCADE")
    due_date    = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow() + datetime.timedelta(hours = 24))

class PigeonRelationship(BaseModel):
    pigeon1   = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    pigeon2   = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    score     = peewee.IntegerField    (null = False, default = 0)

    @property
    def title(self):
        if self.score < -20:
            return "Archnemesis"
        if self.score in range(-20, -5):
            return "Enemy"
        if self.score in range(-5, 0):
            return "Frenemy"
        if self.score in range(0, 15):
            return "Acquaintance"
        if self.score in range(15, 30):
            return "Friend"
        if self.score > 30:
            return "Best Friend"

        return "Hmm"

    @classmethod
    def select_for(cls, pigeon, active = True):
        query = cls.select()
        if active:
            p1 = Pigeon.alias("p1")
            p2 = Pigeon.alias("p2")
            query = query.join(p1, on = cls.pigeon1)
            query = query.switch(cls)
            query = query.join(p2, on = cls.pigeon2)
        query = query.where((cls.pigeon1 == pigeon) | (cls.pigeon2 == pigeon))
        query = query.where(cls.score < -15)
        if active:
            query = query.where(p1.condition == Pigeon.Condition.active)
            query = query.where(p2.condition == Pigeon.Condition.active)
        query = query.order_by(cls.score.asc())
        return query

    @classmethod
    def get_or_create_for(cls, pigeon1, pigeon2):
        query = cls.select()
        query = query.where( (cls.pigeon1 == pigeon1) | (cls.pigeon1 == pigeon2))
        query = query.where( (cls.pigeon2 == pigeon1) | (cls.pigeon2 == pigeon2))
        relationship = query.first()
        if relationship is not None:
            return relationship
        else:
            return cls.create(pigeon1 = pigeon1, pigeon2 = pigeon2)

class LanguageMastery(BaseModel):
    language = LanguageField()
    mastery  = PercentageField(null = False, default = 0)
    pigeon   = peewee.ForeignKeyField (Pigeon, null = False, backref = "language_masteries", on_delete = "CASCADE")

    @property
    def rank(self):
        if self.mastery <= 20:
            return "beginner"
        if self.mastery <= 40:
            return "intermediate"
        if self.mastery <= 60:
            return "advanced"
        if self.mastery <= 80:
            return "fluent"
        else:
            return "native"

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
    item        = peewee.ForeignKeyField (Item, null = True)
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

class Challenge(Activity):
    pigeon1    = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    pigeon2    = peewee.ForeignKeyField (Pigeon, null = False, on_delete = "CASCADE")
    created_at = peewee.DateTimeField   (null = False, default = lambda : datetime.datetime.utcnow())
    guild_id   = peewee.BigIntegerField (null = False)
    accepted   = peewee.BooleanField    (null = True) # null is pending, true is accepted, false is declined.

    @property
    def pigeons(self):
        yield self.pigeon1
        yield self.pigeon2

    @property
    def type(self):
         return self.__class__.__name__

    def validate(self, ctx):
        return None

    def delete_instance(self, *args, **kwargs):
        self.pigeon1.status = Pigeon.status.idle
        self.pigeon2.status = Pigeon.status.idle
        self.pigeon1.save()
        self.pigeon2.save()
        return super().delete_instance(*args, **kwargs)

class Fight(Challenge):
    bet        = peewee.BigIntegerField (null = False, default = 50)
    won        = peewee.BooleanField    (null = True) # null is not ended yet, true means challenger won, false means challengee won

    @property
    def icon_url(self):
        return "https://cdn.discordapp.com/attachments/744172199770062899/779844965705842718/JJAIhfX.gif"

    def validate(self, ctx):
        error_messages = []
        i = 1
        for pigeon in self.pigeons:
            if pigeon.human.gold < self.bet:
                error_messages.append(ctx.translate("pigeon{i}_not_enough_gold").format(bet = self.bet))
            i += 1
        return error_messages

    @property
    def challengee(self):
        return self.pigeon2

    @challengee.setter
    def challenge2(self, value):
        self.pigeon2 = value

    @property
    def challenger(self):
        return self.pigeon1

    @challenger.setter
    def challenger(self, value):
        self.pigeon1 = value

class Date(Challenge):
    gift       = peewee.ForeignKeyField (Item, null = True)
    score      = peewee.IntegerField    (null = False, default = 0) # max 100, min -100

    @property
    def icon_url(self):
        return "https://tubelife.org/wp-content/uploads/2019/08/Valentines-Heart-GIF.gif"