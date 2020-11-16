from enum import Enum
import random

import discord

from src.models import Item, Pigeon
from src.utils.country import Country
import src.config as config

def percentage_chance(chance):
    return random.randint(0,100) < chance

class ActivityRetrieval:
    def __init__(self):
        self._winnings = None
    @property
    def base_embed(self):
        embed = discord.Embed(color = config.bot.get_dominant_color(None))
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed

class ExplorationRetrieval(ActivityRetrieval):
    class Bonus(Enum):
        language = 1
        item     = 2
        tenth    = 3

    def __init__(self, exploration):
        super().__init__()
        self.exploration = exploration
        self.bonuses     = []
        self.fill_bonuses()
        self.item = None

    @property
    def language(self):
        languages = self.exploration.destination.languages()
        if languages:
            languages.sort(key = lambda x : x.alpha_2 == "en")
            return languages[0]

    @property
    def embed(self):
        embed = self.base_embed
        pigeon = self.exploration.pigeon
        text = f"{pigeon.name} soared through the skies for **{self.exploration.duration_in_minutes}** minutes"
        text += f" over a distance of **{int(self.exploration.distance_in_km)}** km"
        text += f" until {pigeon.gender.get_pronoun()} finally reached **{self.exploration.destination.name()}**"

        embed.description = text
        language = self.language
        bonus_messages = []

        if self.Bonus.language in self.bonuses:
            if language is not None:
                bonus_messages.append(f"Some {self.exploration.destination.demonym()} person also taught {pigeon.gender.get_posessive_pronoun()} some {language.name}!")
            else:
                bonus_messages.append(f"{pigeon.gender.get_pronoun().title()} even picked up some of the local language!")

        if self.Bonus.item in self.bonuses:
            items = list(Item.select().where(Item.explorable == True))
            if len(items) > 0:
                self.item = random.choices(items, weights = [x.rarity.weight for x in items], k = 1)[0]
                embed.set_thumbnail(url = self.item.image_url)
                bonus_messages.append(f"On the way {pigeon.gender.get_pronoun()} also found **{self.item.name}**")
        if self.Bonus.tenth in self.bonuses:
            bonus_messages.append(f"Since this is your **{self.exploration.pigeon.explorations.count()}th** exploration, you get a bonus!")

        for bonus_message in bonus_messages:
            embed.add_field(name = "Bonus", value = bonus_message, inline = False)

        embed.add_field(
            name = "Winnings",
            value = get_winnings_value(**self.winnings),
            inline = False
        )
        return embed

    def commit(self):
        pigeon = self.exploration.pigeon

        if self.Bonus.language in self.bonuses:
            if self.language is not None:
                pigeon.study_language(self.language)
        if self.item is not None:
            pigeon.human.add_item(self.item, 1)
        pigeon.update_stats(self.winnings)
        self.exploration.finished = True
        pigeon.status = pigeon.Status.idle
        pigeon.human.save()
        pigeon.save()
        self.exploration.save()

    @property
    def winnings(self):
        if self._winnings is None:
            multiplier = int(1+(len(self.bonuses)*0.5))
            self._winnings = {
                "gold"        : int(self.exploration.gold_worth * multiplier),
                "experience"  : int(self.exploration.xp_worth   * multiplier),
                "food"        : -random.randint(10,40),
                "happiness"   : (-10+(len(self.bonuses)*10)),
                "cleanliness" : -random.randint(10,40)
            }
        return self._winnings

    def fill_bonuses(self):
        if percentage_chance(33):
            self.bonuses.append(self.Bonus.language)
        if percentage_chance(50):
            self.bonuses.append(self.Bonus.item)
        if self.exploration.pigeon.explorations.count() % 10 == 0:
            self.bonuses.append(self.Bonus.tenth)

class MailRetrieval(ActivityRetrieval):
    def __init__(self, mail):
        super().__init__()
        self.mail = mail

    @property
    def embed(self):
        embed = self.base_embed

        embed.add_field(
            name = "Winnings",
            value = get_winnings_value(**self.winnings)
        )

        embed.description = f"{self.mail.pigeon.name} comes back from a long journey to deliver a message!"

        return embed

    @property
    def winnings(self):
        if self._winnings is None:
            self._winnings = {
                    "experience"  : int(self.mail.duration_in_minutes * 0.6),
                    "food"        : -random.randint(10,40),
                    "happiness"   : int(random.randint(10,40)),
                    "cleanliness" : -random.randint(10,40),
                }
        return self._winnings

    def commit(self):
        pigeon.update_stats(self.winnings)
        self.mail.finished = True
        pigeon.status = Pigeon.Status.idle
        pigeon.human.save()
        pigeon.save()
        self.mail.save()


def get_winnings_value(**kwargs):
    lines = []
    for key, value in kwargs.items():
        lines.append(f"{Pigeon.emojis[key]} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)
