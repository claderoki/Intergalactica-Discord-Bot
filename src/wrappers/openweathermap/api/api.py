import requests

from ..enums import TemperatureUnit
from ..models import *

"""
api.openweathermap.org/data/2.5/weather?lat=35&lon=139
api.openweathermap.org/data/2.5/weather?zip=94040,us
"""


class OpenWeatherMapApi:
    base_url = "https://api.openweathermap.org"
    version = 2.5

    __slots__ = ("key")

    def __init__(self, key):
        self.key = key

    @property
    def url(self):
        return self.base_url + "/data/" + str(self.version) + "/weather"

    @property
    def default_params(self):
        return {"appid": self.key}

    def call(self, params):
        url = self.url

        req = requests.get(url, params=params)

        try:
            req.raise_for_status()
        except:
            return None

        json = req.json()

        return City(TemperatureUnit(params["units"]), json)

    def by_id(self, id, unit=TemperatureUnit.Celsius):
        params = self.default_params

        params["id"] = id

        if unit.value != "":
            params["units"] = unit.value

        return self.call(params)

    def by_q(self, name, country_code=None, unit=TemperatureUnit.Celsius):
        params = self.default_params

        q = name

        if country_code is not None:
            q += "," + country_code

        params["q"] = q

        if unit.value != "":
            params["units"] = unit.value

        return self.call(params)
