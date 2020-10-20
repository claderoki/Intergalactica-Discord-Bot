import datetime
import pytz
import math
import pycountry
from timezonefinder import TimezoneFinder

from .coordinate import Coordinate
from .weather_info import WeatherInfo
from .temperature_info import TemperatureInfo



class City:
    __slots__ = ("id", "coordinates", "name",
                 "country_code", "weather_infos",
                 "temperature_info", "unit", "country")

    def __init__(self, unit, data):
        self.unit = unit
        self.__init_data(data)



    def __init_data(self, data):
        self.id                 = data["id"]
        self.coordinates        = Coordinate(data["coord"]["lat"], data["coord"]["lon"])
        self.name               = data["name"]
        self.country_code       = data["sys"]["country"]
        self.weather_infos      = [WeatherInfo(self, x) for x in data["weather"]]
        self.temperature_info   = TemperatureInfo(self, data["main"])
        self.country            = pycountry.countries.get(alpha_2=self.country_code)

    def __str__(self):
        return "City object: name=" + self.name + ", country_code=" + self.country_code

    @property
    def timezone(self):
        return pytz.timezone(TimezoneFinder().timezone_at(lng = self.coordinates.longitude, lat = self.coordinates.latitude))

    @property
    def current_time(self):
        loc_dt = datetime.datetime.now().astimezone(self.timezone)
        return loc_dt.strftime('%H:%M')

    @property
    def corona_count(self):
        pass

    def get_distance(self, other_city):
        R = 6373.0

        lat1 = math.radians(self.coordinates.latitude)
        lon1 = math.radians(self.coordinates.longitude)

        lat2 = math.radians(other_city.coordinates.latitude)
        lon2 = math.radians(other_city.coordinates.longitude)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c