import random

import pycountry
from countryinfo import CountryInfo

class Country(CountryInfo):
    def __init__(self, alpha_2):
        super().__init__(alpha_2)
        self._country = pycountry.countries.get(alpha_2 = alpha_2)

    def name(self):
        return self._country.name

    def languages(self):
        return [pycountry.languages.get(alpha_2 = x) for x in super().languages()]

    @property
    def alpha_2(self):
        return self.iso()["alpha2"]

    @classmethod
    def from_alpha_2(cls, alpha_2):
        return cls(alpha_2)

    @classmethod
    def random(cls):
        alpha_2 = None
        countries = list(pycountry.countries)
        while alpha_2 is None:
            alpha_2 = random.choice(countries).alpha_2
            try:
                CountryInfo(alpha_2).capital()
                CountryInfo(alpha_2).capital_latlng()
            except KeyError:
                alpha_2 = None

        return cls.from_alpha_2(alpha_2)


if __name__ == "__main__":
    country = Country.from_alpha_2("nl")
    print(country.name())
    print(country.languages())