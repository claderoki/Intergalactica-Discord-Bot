import discord
import random
from enum import Enum
import asyncio


class Game:
    bet = 5

    class Reel(Enum):
        ORANGE      = ("🍊", 10)
        WATERMELON  = ("🍉", 14)
        BAR         = ("🍫", 250)
        CHERRY      = ("🍒", 7)
        SEVEN       = ("🥝", 1000)

    values = list(Reel)


    def __init__(self, ui):
        self.ui = ui

    def _get_different_emoji(self, emoji):
        different_emoji = None
        while different_emoji is None or different_emoji == emoji:
            different_emoji = random.choice(self.values).value[0]

        return different_emoji


    async def start(self):
        first,second,third = random.choice(self.values), random.choice(self.values), random.choice(self.values)

        if first == self.Reel.CHERRY:
            if second == self.Reel.CHERRY:
                win = self.Reel.CHERRY.value[1] if third == self.Reel.CHERRY else 5
            else:
                win = 2
        else:
            if first == second == third:
                win = first.value[1]
            else:
                win = -1

        await self.ui.show_reel((first,second,third), win)
