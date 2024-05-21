import datetime
import math
import random
from enum import Enum
from typing import Iterable, List

import discord
import peewee
from dateutil.relativedelta import relativedelta

from src.utils.enums import Gender
from .base import BaseModel, EnumField, EmojiField, PercentageField, CountryField, LanguageField, \
    LongTextField, BaseModelSelect
from .helpers import create
from .human import Human, Item, ItemCategory
from .. import constants
from ..utils.stats import Winnings, PigeonStat, HumanStat


@create()
class Activity(BaseModel):
    start_date = peewee.DateTimeField(null=True, default=lambda: datetime.datetime.utcnow())
    end_date = peewee.DateTimeField(null=True)
    finished = peewee.BooleanField(null=False, default=False)

    @property
    def end_date_passed(self):
        return datetime.datetime.utcnow() >= self.end_date

    @property
    def duration_in_minutes(self):
        return int((self.end_date - self.start_date).total_seconds() / 60.0)


@create()
class TravelActivity(Activity):
    residence = CountryField(null=True)
    destination = CountryField(null=True)

    @property
    def distance_in_km(self):
        if self.residence is None or self.destination is None:
            return

        R = 6373.0

        lat1, lon1 = [math.radians(x) for x in self.residence.capital_latlng()]
        lat2, lon2 = [math.radians(x) for x in self.destination.capital_latlng()]

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_duration(self):
        min_time_in_minutes = 45
        max_time_in_minutes = 180
        km = self.distance_in_km
        if km is None:
            return random.randint(min_time_in_minutes, max_time_in_minutes + 1)

        duration = int(km / 40)
        if duration < min_time_in_minutes:
            duration = min_time_in_minutes
        elif duration > max_time_in_minutes:
            duration = max_time_in_minutes
        return duration


class Gendered:
    def get_gender(self) -> Gender:
        pass


@create()
class Pigeon(BaseModel, Gendered):
    emojis = {
        "name": "📛",
        "gold": constants.GOLD_EMOJI,
        "experience": "📊",
        "cleanliness": "💩",
        "food": "🌾",
        "happiness": "🌻",
        "health": "❤️",
    }

    class Status(Enum):
        idle = "💤"
        mailing = "📧"
        exploring = "🗺️"
        fighting = "⚔️"
        dating = "❤️"
        space_exploring = "🗺️"
        jailed = ""

        def get_verb(self):
            if self == self.space_exploring:
                return 'exploring space'
            return self.name

    class Condition(Enum):
        active = 1
        ran_away = 2
        dead = 3

    name = peewee.TextField(null=False)
    human = peewee.ForeignKeyField(Human, backref="pigeons")
    condition = EnumField(Condition, default=Condition.active)
    experience = peewee.IntegerField(null=False, default=0)
    cleanliness = PercentageField(null=False, default=100)
    happiness = PercentageField(null=False, default=100)
    food = PercentageField(null=False, default=100)
    health = PercentageField(null=False, default=100)
    status = EnumField(Status, default=Status.idle)
    gender = EnumField(Gender, default=Gender.other)
    pvp = peewee.BooleanField(null=False, default=False)
    last_used_pvp = peewee.DateTimeField(null=True)
    jailed_until = peewee.DateTimeField(null=True)
    pooped_on_count = peewee.IntegerField(null=False, default=0)
    poop_victim_count = peewee.IntegerField(null=False, default=0)

    def get_gender(self) -> Gender:
        return self.gender

    @property
    def is_jailed(self):
        if self.jailed_until is None:
            return False
        return self.jailed_until > datetime.datetime.utcnow()

    @property
    def can_disable_pvp(self):
        if self.last_used_pvp is None:
            return True

        difference = relativedelta(datetime.datetime.utcnow(), self.last_used_pvp)
        return difference.hours >= 12 or difference.days > 1

    @property
    def pvp_action_available(self):
        if self.last_used_pvp is None:
            return True

        difference = relativedelta(datetime.datetime.utcnow(), self.last_used_pvp)

        return difference.hours >= 3 or difference.days >= 1 or difference.weeks >= 1 or difference.months >= 1

    def study_language(self, language, mastery=1):
        language, _ = LanguageMastery.get_or_create(pigeon=self, language=language)
        language.mastery += mastery
        language.save()

    def update_winnings(self, winnings: Winnings):
        stats = winnings.to_dict()
        item_id = stats.get('item')
        if item_id:
            # todo: add item
            del stats['item']

        self.update_stats(stats)

    def update_stats(self, data, increment=True, save=True):
        human = self.bot.get_human(user=self.human.user_id)
        for key, value in data.items():
            if key == "gold":
                human.gold += value
            else:
                if increment:
                    setattr(self, key, (getattr(self, key) + value))
                else:
                    setattr(self, key, value)

                if key == "health":
                    if self.health <= 0:
                        self.condition = self.Condition.dead
                        SystemMessage.create(text=self.bot.translate("pigeon_dead"), human=human)
        try:
            if save:
                self.save()
                human.save()
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
    def fights(self):
        query = Fight.select()
        query = query.where((Fight.challenger == self) | (Fight.challengee == self))
        return query

    def get_stats(self) -> List[PigeonStat]:
        return [
            PigeonStat.food(self.food),
            PigeonStat.health(self.health),
            PigeonStat.cleanliness(self.cleanliness),
            PigeonStat.happiness(self.happiness),
            PigeonStat.experience(self.experience),
        ]


@create()
class PigeonRelationship(BaseModel):
    pigeon1 = peewee.ForeignKeyField(Pigeon, null=False, on_delete="CASCADE")
    pigeon2 = peewee.ForeignKeyField(Pigeon, null=False, on_delete="CASCADE")
    score = peewee.IntegerField(null=False, default=0)

    @staticmethod
    def _get_title(score):
        if score < -20:
            return "Archnemesis"
        if score in range(-20, -5):
            return "Enemy"
        if score in range(-5, 0):
            return "Frenemy"
        if score in range(0, 15):
            return "Acquaintance"
        if score in range(15, 30):
            return "Friend"
        if score > 30:
            return "Best Friend"

        return "Hmm"

    @property
    def title(self):
        return self._get_title(self.score)

    @classmethod
    def select_for(cls, pigeon, active=True):
        query = cls.select()
        if active:
            p1 = Pigeon.alias("p1")
            p2 = Pigeon.alias("p2")
            query = query.join(p1, on=cls.pigeon1)
            query = query.switch(cls)
            query = query.join(p2, on=cls.pigeon2)
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
        query = query.where((cls.pigeon1 == pigeon1) | (cls.pigeon1 == pigeon2))
        query = query.where((cls.pigeon2 == pigeon1) | (cls.pigeon2 == pigeon2))
        relationship = query.first()
        if relationship is not None:
            return relationship
        else:
            return cls.create(pigeon1=pigeon1, pigeon2=pigeon2)


@create()
class LanguageMastery(BaseModel):
    language = LanguageField()
    mastery = PercentageField(null=False, default=0)
    pigeon = peewee.ForeignKeyField(Pigeon, null=False, backref="language_masteries", on_delete="CASCADE")

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


@create()
class SystemMessage(BaseModel):
    human = peewee.ForeignKeyField(Human, null=False, backref="system_messages", on_delete="CASCADE")
    text = peewee.TextField(null=False)
    read = peewee.BooleanField(null=False, default=False)

    @property
    def embed(self):
        return discord.Embed(description=self.text)


@create()
class Mail(TravelActivity):
    recipient = peewee.ForeignKeyField(Human, null=False, backref="inbox", on_delete="CASCADE")
    sender = peewee.ForeignKeyField(Pigeon, null=False, backref="outbox", on_delete="CASCADE")
    gold = peewee.IntegerField(null=False, default=0)
    item = peewee.ForeignKeyField(Item, null=True)
    message = EmojiField(null=True)
    read = peewee.BooleanField(null=False, default=True)


@create()
class Exploration(TravelActivity):
    name = peewee.TextField(null=True)
    pigeon = peewee.ForeignKeyField(Pigeon, null=False, backref="explorations", on_delete="CASCADE")

    class Meta:
        table_name = "legacy_exploration"

    @property
    def xp_worth(self):
        return math.ceil(self.duration_in_minutes)

    @property
    def gold_worth(self):
        return math.ceil(self.duration_in_minutes * 0.6)


@create()
class Challenge(Activity):
    pigeon1 = peewee.ForeignKeyField(Pigeon, null=False, on_delete="CASCADE")
    pigeon2 = peewee.ForeignKeyField(Pigeon, null=False, on_delete="CASCADE")
    created_at = peewee.DateTimeField(null=False, default=lambda: datetime.datetime.utcnow())
    guild_id = peewee.BigIntegerField(null=False)
    accepted = peewee.BooleanField(null=True)  # null is pending, true is accepted, false is declined.

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
        self.pigeon1.status = Pigeon.Status.idle
        self.pigeon2.status = Pigeon.Status.idle
        self.pigeon1.save()
        self.pigeon2.save()
        return super().delete_instance(*args, **kwargs)


@create()
class Fight(Challenge):
    bet = peewee.BigIntegerField(null=False, default=50)
    won = peewee.BooleanField(null=True)  # null is not ended yet, true means challenger won, false means challengee won

    @property
    def icon_url(self):
        return "https://cdn.discordapp.com/attachments/744172199770062899/779844965705842718/JJAIhfX.gif"

    def validate(self, ctx):
        error_messages = []
        i = 1
        for pigeon in self.pigeons:
            human = self.bot.get_human(user=pigeon.human.user_id)
            if human.gold < self.bet:
                error_messages.append(ctx.translate(f"pigeon{i}_not_enough_gold").format(bet=self.bet))
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


@create()
class Date(Challenge):
    gift = peewee.ForeignKeyField(Item, null=True)
    score = peewee.IntegerField(null=False, default=0)  # max 100, min -100

    @property
    def icon_url(self):
        return "https://tubelife.org/wp-content/uploads/2019/08/Valentines-Heart-GIF.gif"


@create()
class ExplorationPlanet(BaseModel):
    name = peewee.TextField()
    image_url = peewee.TextField()


@create()
class ExplorationPlanetLocation(BaseModel):
    name = peewee.TextField()
    planet = peewee.ForeignKeyField(ExplorationPlanet)
    image_url = peewee.TextField(null=True)
    active = peewee.BooleanField(default=False)
    actions: BaseModelSelect


@create()
class ExplorationAction(BaseModel):
    name = peewee.TextField()
    symbol = peewee.TextField()
    location = peewee.ForeignKeyField(ExplorationPlanetLocation, backref='actions')
    planet = peewee.ForeignKeyField(ExplorationPlanet)

    scenarios: BaseModelSelect


class ToWinnings:
    def to_winnings(self) -> Winnings:
        stats = [
            HumanStat.gold(self.gold),
            PigeonStat.health(self.health),
            PigeonStat.happiness(self.happiness),
            PigeonStat.experience(self.experience),
            PigeonStat.cleanliness(self.cleanliness),
            PigeonStat.food(self.food)
        ]
        if self.item is not None:
            stats.append(HumanStat.item(self.item))
        return Winnings(*[x for x in stats if x.amount])


@create()
class ExplorationActionScenario(BaseModel, ToWinnings):
    text = LongTextField()
    action = peewee.ForeignKeyField(ExplorationAction, backref='scenarios')
    gold = peewee.IntegerField(default=0)
    health = peewee.IntegerField(default=0)
    happiness = peewee.IntegerField(default=0)
    experience = peewee.IntegerField(default=0)
    cleanliness = peewee.IntegerField(default=0)
    food = peewee.IntegerField(default=0)
    item = peewee.ForeignKeyField(Item, null=True)
    item_category = peewee.ForeignKeyField(ItemCategory, null=True)


@create()
class SpaceExploration(BaseModel):
    class Meta:
        table_name = 'exploration'

    location = peewee.ForeignKeyField(ExplorationPlanetLocation, column_name='planet_location_id')
    start_date = peewee.DateTimeField()
    arrival_date = peewee.DateTimeField()
    end_date = peewee.DateTimeField(null=True)
    finished = peewee.BooleanField(default=False)
    pigeon = peewee.ForeignKeyField(Pigeon)
    actions_remaining = peewee.IntegerField()
    total_actions = peewee.IntegerField()

    @classmethod
    def a(cls):
        pass


@create()
class SpaceExplorationScenarioWinnings(BaseModel, ToWinnings):
    class Meta:
        table_name = 'exploration_winnings'

    action = peewee.ForeignKeyField(ExplorationAction)
    exploration = peewee.ForeignKeyField(SpaceExploration)
    gold = peewee.IntegerField(default=0)
    health = peewee.IntegerField(default=0)
    happiness = peewee.IntegerField(default=0)
    experience = peewee.IntegerField(default=0)
    cleanliness = peewee.IntegerField(default=0)
    food = peewee.IntegerField(default=0)
    item = peewee.ForeignKeyField(Item, null=True)

    @classmethod
    def for_exploration(cls, exploration_id: int) -> peewee.Query:
        return SpaceExplorationScenarioWinnings.select() \
            .where(SpaceExplorationScenarioWinnings.exploration == exploration_id)
