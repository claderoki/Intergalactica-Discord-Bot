import random

import discord
import requests

from src.wrappers.color_thief import ColorThief


class ColorHelper:
    @classmethod
    def __get_dominant_color(cls, url):
        color_thief = ColorThief(requests.get(url, stream=True).raw)
        dominant_color = color_thief.get_color(quality=1)
        return discord.Color.from_rgb(*dominant_color)

    @classmethod
    def get_dominant_color(cls, guild=None) -> discord.Colour:
        return discord.Color.from_rgb(242, 180, 37)

    @classmethod
    def get_random_color(cls, start_range=80, end_range=255) -> discord.Colour:
        # from 80 to 255 because the majority of discord users use the dark theme, and anything under 80 is too bright to be comfortably visible.
        if end_range > 255:
            end_range = 255

        if start_range < 0:
            start_range = 0

        r, g, b = [random.randint(start_range, end_range) for _ in range(3)]
        random_color = discord.Color(0).from_rgb(r, g, b)
        return random_color
