import random

from emoji import emojize
import pycountry
from countryinfo import CountryInfo

class CountryNotFound(Exception):
    pass

class Country(CountryInfo):
    def __init__(self, alpha_2):
        super().__init__(alpha_2)
        if super().name() == alpha_2:
            raise CountryNotFound("Not found.")
        self._country = pycountry.countries.get(alpha_2 = alpha_2)

    def name(self):
        return self._country.name

    def languages(self):
        return [pycountry.languages.get(alpha_2 = x) for x in super().languages()]

    def currencies(self):
        return [pycountry.currencies.get(alpha_3 = x) for x in super().currencies()]

    @property
    def alpha_2(self):
        return self.iso()["alpha2"]

    def __str__(self):
        return self.alpha_2

    @classmethod
    def from_alpha_2(cls, alpha_2):
        return cls(alpha_2)

    def flag(self):
        return f"https://www.countryflags.io/{self.alpha_2.lower()}/flat/64.png"

    @property
    def flag_emoji(self):
        return "".join(emojize(f":regional_indicator_symbol_letter_{x}:") for x in self.alpha_2.lower())

    @classmethod
    def random(cls):
        alpha_2 = None
        countries = list(pycountry.countries)
        while alpha_2 is None:
            alpha_2 = random.choice(countries).alpha_2
            try:
                CountryInfo(alpha_2).capital_latlng()
            except KeyError:
                alpha_2 = None

        return cls.from_alpha_2(alpha_2)

if __name__ == "__main__":
    country = Country.from_alpha_2("efw")
    print(country.name())