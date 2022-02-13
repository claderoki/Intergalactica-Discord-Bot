import random
import re


class StringFormatter:
    __slots__ = ()


class Uwu(StringFormatter):
    expressions = (
        (r"(?:r|l)", r"w"),
        (r"(?:R|L)", r"W"),
        (r"n([aeiou])", r"ny\1"),
        (r"N([aeiou])", r"Ny\1"),
        (r"N([AEIOU])", r"Ny\1"),
        (r"ove", r"uv"),
        (r"!+", lambda: " " + random.choice(("(・`ω´・)", ";;w;;", "owo", "UwU", ">w<", "^w^")))
    )

    @classmethod
    def format(cls, text):
        for expression, replace in cls.expressions:
            pattern = re.compile(expression)
            text = re.sub(pattern, replace if not callable(replace) else replace(), text)
        return text
