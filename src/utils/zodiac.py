import datetime
from enum import Enum

from emoji import emojize


class DateRange:
    def __init__(self, start, stop=None, step=datetime.timedelta(days=1)):
        self.start = start
        self.stop = stop or datetime.datetime.utcnow()
        self.step = step

        self.validate()

    def validate(self):
        assert self.start < self.stop
        assert isinstance(self.start, (datetime.datetime, datetime.date))
        assert isinstance(self.stop, (datetime.datetime, datetime.date))
        assert isinstance(self.step, datetime.timedelta)

    def __iter__(self):
        date = self.start
        while date < self.stop:
            yield date
            date += self.step

    def __contains__(self, date):
        return date >= self.start and date <= self.stop


class ZodiacSign(Enum):
    sagittarius = 0
    capricorn = 1
    aquarius = 2
    pisces = 3
    aries = 4
    taurus = 5
    gemini = 6
    cancer = 7
    leo = 8
    virgo = 9
    libra = 10
    scorpio = 11

    @property
    def emoji(self):
        return emojize(f":{self.name.title()}:")

    @classmethod
    def from_date(cls, date):
        if date.month == 12:
            return cls.sagittarius if (date.day < 22) else cls.capricorn
        elif date.month == 1:
            return cls.capricorn if (date.day < 20) else cls.aquarius
        elif date.month == 2:
            return cls.aquarius if (date.day < 19) else cls.pisces
        elif date.month == 3:
            return cls.pisces if (date.day < 21) else cls.aries
        elif date.month == 4:
            return cls.aries if (date.day < 20) else cls.taurus
        elif date.month == 5:
            return cls.taurus if (date.day < 21) else cls.gemini
        elif date.month == 6:
            return cls.gemini if (date.day < 21) else cls.cancer
        elif date.month == 7:
            return cls.cancer if (date.day < 23) else cls.leo
        elif date.month == 8:
            return cls.leo if (date.day < 23) else cls.virgo
        elif date.month == 9:
            return cls.virgo if (date.day < 23) else cls.libra
        elif date.month == 10:
            return cls.libra if (date.day < 23) else cls.scorpio
        elif date.month == 11:
            return cls.scorpio if (date.day < 22) else cls.sagittarius


if __name__ == "__main__":
    dates = DateRange(datetime.datetime(2020, 11, 10))
    for date in dates:
        print(date)
    print(datetime.datetime(2020, 11, 10) in dates)

    sign = ZodiacSign.from_date(datetime.datetime(2020, 11, 10))
    print(sign.emoji)
