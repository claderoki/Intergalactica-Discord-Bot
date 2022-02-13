import random
from enum import Enum


class Game:
    bet = 5

    class Reel(Enum):
        cherry = ("🍒", 15)
        orange = ("🍊", 25)
        watermelon = ("🍉", 75)
        bar = ("🍫", 250)
        seven = ("🥝", 500)

        @property
        def probability(self):
            pass

        @property
        def emoji(self):
            return self.value[0]

        @property
        def payout(self):
            return self.value[1]

    values = list(Reel)

    def __init__(self, ui):
        self.ui = ui

    async def start(self):
        reel = random.choices(self.values, weights=(17, 15, 15, 10, 5), k=3)
        # reel = random.choices(self.values, weights = (30, 25, 20, 10, 5), k = 3)
        first, second, third = reel

        cherry_count = len([x for x in reel if x == self.Reel.cherry])

        if first == second == third:
            win = first.payout
        elif cherry_count > 0 and first == self.Reel.cherry:
            win = cherry_count * 2
        else:
            win = -3

        await self.ui.show_reel(reel, win)
