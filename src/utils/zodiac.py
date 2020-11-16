
class ZodiacSign:
    __slots__ = ("name", "emoji")

    def __init__(self, name, emoji):
        self.name = name
        self.emoji = emoji

    @classmethod
    def from_date(cls, date):
        if date.month == 12:
            return cls.sagittarius() if (date.day < 22) else cls.capricorn()
        elif date.month == 1:
            return cls.capricorn() if (date.day < 20) else cls.aquarius()
        elif date.month == 2:
            return cls.aquarius() if (date.day < 19) else cls.pisces()
        elif date.month == 3:
            return cls.pisces() if (date.day < 21) else cls.aries()
        elif date.month == 4:
            return cls.aries() if (date.day < 20) else cls.taurus()
        elif date.month == 5:
            return cls.taurus() if (date.day < 21) else cls.gemini()
        elif date.month == 6:
            return cls.gemini() if (date.day < 21) else cls.cancer()
        elif date.month == 7:
            return cls.cancer() if (date.day < 23) else cls.leo()
        elif date.month == 8:
            return cls.leo() if (date.day < 23) else cls.virgo()
        elif date.month == 9:
            return cls.virgo() if (date.day < 23) else cls.libra()
        elif date.month == 10:
            return cls.libra() if (date.day < 23) else cls.scorpio()
        elif date.month == 11:
            return cls.scorpio() if (date.day < 22) else cls.sagittarius()

    @classmethod
    def sagittarius(cls):
        return cls("sagittarius", "♐")

    @classmethod
    def capricorn(cls):
        return cls("capricorn", "♑")

    @classmethod
    def aquarius(cls):
        return cls("aquarius", "♒")

    @classmethod
    def pisces(cls):
        return cls("pisces", "♓")

    @classmethod
    def aries(cls):
        return cls("aries", "♈")

    @classmethod
    def taurus(cls):
        return cls("taurus", "♉")

    @classmethod
    def gemini(cls):
        return cls("gemini", "♊")

    @classmethod
    def cancer(cls):
        return cls("cancer", "♋")

    @classmethod
    def leo(cls):
        return cls("leo", "♌")

    @classmethod
    def virgo(cls):
        return cls("virgo", "♍")

    @classmethod
    def libra(cls):
        return cls("libra", "♎")

    @classmethod
    def scorpio(cls):
        return cls("scorpio", "♏")