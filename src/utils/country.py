import random

import pycountry
from countryinfo import CountryInfo
from covid import Covid
from emoji import emojize


class CountryNotFound(Exception):
    pass


class Country(CountryInfo):
    def __init__(self, argument):
        super().__init__(argument)
        if super().name() == argument:
            raise CountryNotFound("Not found.")
        try:
            iso = self.iso()
        except KeyError:
            raise CountryNotFound("Not found.")

        self._country = pycountry.countries.get(alpha_2=iso["alpha2"])

        self._covid_status = None

    def name(self):
        return self._country.name

    def languages(self):
        return [pycountry.languages.get(alpha_2=x) for x in super().languages()]

    def currencies(self):
        return [pycountry.currencies.get(alpha_3=x) for x in super().currencies()]

    @property
    def covid_status(self):
        if self._covid_status is None:
            covid = Covid()
            self._covid_status = covid.get_status_by_country_name(self.name())

        return self._covid_status

    @property
    def alpha_2(self):
        return self.iso()["alpha2"]

    def __str__(self):
        return self.alpha_2

    @classmethod
    def from_alpha_2(cls, alpha_2):
        return cls(alpha_2)

    @classmethod
    def from_alpha_3(cls, alpha_3):
        return cls(alpha_3)

    @classmethod
    def from_name(cls, name):
        return cls(name)

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
    country = Country.from_alpha_2("nl")
    print(country.covid_status)
