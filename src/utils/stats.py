import emoji


class Stat:
    def __init__(self, name: str, value, emoji):
        self.name = name
        self.value = value
        self.emoji = emoji


class HumanStat(Stat):
    @classmethod
    def gold(cls, amount: int) -> 'HumanStat':
        return cls('gold', amount, emoji.emojize(":euro:"))

    @classmethod
    def item(cls, id: int) -> 'HumanStat':
        return cls('item', id, None)


class PigeonStat(Stat):
    @classmethod
    def cleanliness(cls, amount: int) -> 'PigeonStat':
        return cls('cleanliness', amount, '💩')

    @classmethod
    def food(cls, amount: int) -> 'PigeonStat':
        return cls('food', amount, '🌾')

    @classmethod
    def experience(cls, amount: int) -> 'PigeonStat':
        return cls('experience', amount, '📊')

    @classmethod
    def health(cls, amount: int) -> 'PigeonStat':
        return cls('health', amount, '❤️')

    @classmethod
    def happiness(cls, amount: int) -> 'PigeonStat':
        return cls('happiness', amount, '🌻')

    @classmethod
    def gold_modifier(cls, amount: float) -> 'PigeonStat':
        return cls('gold_modifier', amount, '❤')


class Winnings:
    def __init__(self, *stats: Stat):
        self.stats = stats

    def format(self, separator: str = ' ', include_empty: bool = False) -> str:
        values = []
        for stat in self.stats:
            if not include_empty and not stat.value:
                continue
            values.append(f'{stat.emoji} {stat.value}')
        return separator.join(values)

    def to_dict(self):
        return {x.name: x.value for x in self.stats}
