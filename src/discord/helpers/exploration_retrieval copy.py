from enum import Enum
import random

import discord

from src.models import Item, Pigeon, PigeonRelationship
from src.utils.country import Country
import src.config as config

def percentage_chance(chance):
    return random.randint(0,100) < chance



class ActivityRetrieval:
    __slots__ = ("pigeon", "bonuses", "activity")

    def __init__(self, pigeon: Pigeon, activity):
        self.pigeon = pigeon
        self.bonuses = []
        self.activity = activity

    def calculate_winnings():
        pass

    def get_winnings():
        pass

class PigeonExplorationRetrieval:
    __slots__ = ("")

    def __init__(self, pigeon):
        super().__init__(pigeon)

"""

class ActivityRetrieval:
    def __init__(self):
        self._winnings = None
    @property
    def base_embed(self):
        embed = discord.Embed(color = config.bot.get_dominant_color(None))
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed


class ExplorationRetrieval(ActivityRetrieval):
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
        text = f"`{pigeon.name}` soared through the skies for **{self.exploration.duration_in_minutes}** minutes"
        text += f" over a distance of **{int(self.exploration.distance_in_km)}** km"
        text += f" until {pigeon.gender.get_pronoun()} finally reached **{self.exploration.destination.name()}**"

        embed.description = text

        bonus_messages = {}
        if self.Bonus.language in self.bonuses:
            language = self.language
            if language is not None:
                bonus_messages[self.Bonus.language] = f"A helpful {self.exploration.destination.demonym()} person also taught {pigeon.gender.get_pronoun(object = True)} some {language.name}!"
            else:
                bonus_messages[self.Bonus.language] = f"{pigeon.gender.get_pronoun().title()} even picked up some of the local language!"

        if self.Bonus.item in self.bonuses:
            self.item = Item.get_random()

            embed.set_thumbnail(url = self.item.image_url)
            lines = []
            lines.append(f"On the way {pigeon.gender.get_pronoun()} also found **{self.item.name}**")
            if self.item.usable:
                lines.append(f"*{self.item.description}*")
            bonus_messages[self.Bonus.item] = "\n".join(lines)
        if self.Bonus.tenth in self.bonuses:
            bonus_messages[self.Bonus.tenth] = f"Since this is your **{self.exploration.pigeon.explorations.count()}th** exploration, you get a bonus!"
        if self.Bonus.hundredth in self.bonuses:
            bonus_messages[self.Bonus.hundredth] = f"Since this is your **{self.exploration.pigeon.explorations.count()}th** exploration, you get a bonus!"
        if self.Bonus.wing_damage in self.bonuses:
            query = PigeonRelationship.select_for(pigeon)
            relationship = query.first()
            attacker_name = "a random pigeon"
            if relationship is not None:
                other = relationship.pigeon1 if relationship.pigeon1 != pigeon else relationship.pigeon2
                attacker_name = f"`{other.name}`"
            bonus_messages[self.Bonus.wing_damage] = f"During the flight, {pigeon.name} got attacked by {attacker_name}."

        buffs = []
        for bonus, bonus_message in bonus_messages.items():
            if bonus.buff_code is not None:
                buffs.append(Buff.get(code = bonus.buff_code))
            symbol = "+" if bonus.amount > 0 else ""

            embed.add_field(name = f"Bonus {Pigeon.emojis['gold']} {symbol}{bonus.amount}", value = bonus_message, inline = False)

        if len(buffs) > 0:
            lines = []
            for buff in buffs:
                lines.append(f"**{buff.name}**: *{buff.description}*")
            embed.add_field(name = "Buffs gained", value = "\n".join(lines), inline = False)

        embed.add_field(
            name = "Total Winnings",
            value = get_winnings_value(**self.winnings),
            inline = False
        )
        return embed

    @property
    def winnings(self):
        if self._winnings is None:
            gold_earned = self.exploration.gold_worth
            for bonus in self.bonuses:
                gold_earned += bonus.amount

            xp_earned = self.exploration.xp_worth
            xp_earned += (len([x for x in self.bonuses if x.amount >= 0]) * 20)

            health = 0
            if self.Bonus.wing_damage in self.bonuses:
                health = -20

            self._winnings = {
                "gold"        : int(gold_earned),
                "experience"  : int(xp_earned),
                "food"        : -random.randint(10,20),
                "happiness"   : (0+(len(self.bonuses)*10)),
                "cleanliness" : -random.randint(10,20),
                "health"      : health,
            }
        return self._winnings

    def fill_bonuses(self):
        for bonus in self.Bonus:
            chance = bonus.chance
            if chance is not None:
                if percentage_chance(chance):
                    self.bonuses.append(bonus)

        if self.exploration.pigeon.explorations.count() % 100 == 0:
            self.bonuses.append(self.Bonus.hundredth)
        elif self.exploration.pigeon.explorations.count() % 10 == 0:
            self.bonuses.append(self.Bonus.tenth)

    def commit(self):
        pigeon = self.exploration.pigeon
        if self.Bonus.language in self.bonuses and self.language is not None:
            pigeon.study_language(self.language)
        if self.item is not None:
            pigeon.human.add_item(self.item, amount = 1, found = True)
        pigeon.status = pigeon.Status.idle
        pigeon.update_stats(self.winnings)
        for bonus in self.bonuses:
            if bonus.buff_code is not None:
                pigeon.create_buff(bonus.buff_code, create_system_message = False)
        self.exploration.finished = True
        self.exploration.save()

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

        embed.description = f"`{self.mail.sender.name}` comes back from a long journey to deliver a message!"

        return embed

    @property
    def winnings(self):
        if self._winnings is None:
            self._winnings = {
                    "experience"  : int(self.mail.duration_in_minutes * 0.6),
                    "food"        : -random.randint(5,35),
                    "cleanliness" : -random.randint(5,35),
                }
        return self._winnings

    def commit(self):
        pigeon = self.mail.sender
        pigeon.status = Pigeon.Status.idle
        pigeon.update_stats(self.winnings)
        self.mail.finished = True
        self.mail.save()

def get_winnings_value(**kwargs):
    lines = []
    for key, value in kwargs.items():
        if value != 0:
            lines.append(f"{Pigeon.emojis[key]} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)
"""