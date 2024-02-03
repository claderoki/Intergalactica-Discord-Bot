from typing import Dict

from emoji import emojize


class Stat:
    def __init__(self, name: str, amount, info=None, emoji=None):
        self.name = name
        self.amount = amount
        self.info = info
        self.emoji = emoji

    def combine(self, stat: 'Stat'):
        self.amount += stat.amount

    def copy(self) -> 'Stat':
        return Stat(self.name, self.amount, self.info, self.emoji)


class HumanStat(Stat):
    @classmethod
    def gold(cls, amount: int) -> 'HumanStat':
        return cls('gold', amount, emoji=emojize(":euro:"))

    @classmethod
    def item(cls, id: int) -> 'HumanStat':
        return cls('item', 1, info=id)


class PigeonStat(Stat):
    @classmethod
    def cleanliness(cls, amount: int) -> 'PigeonStat':
        return cls('cleanliness', amount, emoji='💩')

    @classmethod
    def food(cls, amount: int) -> 'PigeonStat':
        return cls('food', amount, emoji='🌾')

    @classmethod
    def experience(cls, amount: int) -> 'PigeonStat':
        return cls('experience', amount, emoji='📊')

    @classmethod
    def health(cls, amount: int) -> 'PigeonStat':
        return cls('health', amount, emoji='❤️')

    @classmethod
    def happiness(cls, amount: int) -> 'PigeonStat':
        return cls('happiness', amount, emoji='🌻')

    @classmethod
    def gold_modifier(cls, amount: float) -> 'PigeonStat':
        return cls('gold_modifier', amount, emoji='❤')


class Winnings:
    def __init__(self, *stats: Stat):
        self._stats = list(stats)

    def format(self, separator: str = ' ', include_empty: bool = False) -> str:
        values = []
        for stat in self._stats:
            if not include_empty and not stat.amount:
                continue
            values.append(f'{stat.emoji} {stat.info or stat.amount}')
        return separator.join(values)

    def merge(self, winnings: 'Winnings'):
        for stat in self._stats:
            for other_stat in winnings._stats:
                if stat.name == other_stat.name:
                    stat.combine(other_stat)

    def to_dict(self):
        return {x.name: x.info or x.amount for x in self._stats}

    def add_stat(self, stat: Stat):
        self._stats.append(stat)

    @classmethod
    def combine_all(cls, *winnings: 'Winnings'):
        stats: Dict[str, Stat] = {}
        for winning in winnings:
            for stat in winning._stats:
                if stat.name in stats:
                    stats[stat.name].combine(stat)
                else:
                    stats[stat.name] = stat.copy()
        return Winnings(*stats)
