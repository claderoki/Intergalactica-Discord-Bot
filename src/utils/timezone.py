import datetime
import requests
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import pytz

user_agent = "timezone_locator"

class Timezone:
    geolocator = Nominatim(user_agent=user_agent)

    __slots__ = ("name", "tz", "country_code", "country")

    def __init__(self, name):
        self.name = name
        self.tz = pytz.timezone(self.name)
        self.country_code = self._get_country_code()
        self.country = self.geolocator.geocode(self.country_code, language="en")

        
    def _get_country_code(self):
        for code in pytz.country_timezones:
            if self.name in pytz.country_timezones[code]:
                return code

    @classmethod
    def from_city(cls, name):
        location = cls.geolocator.geocode(name)
        return cls.from_location(location.longitude, location.latitude)

    @classmethod
    def from_hour(cls, hour):
        for tz_name in pytz.common_timezones_set:
            tz = pytz.timezone(tz_name)
            dt = datetime.datetime.now().astimezone(tz)
            if dt.hour == hour:
                return cls(tz_name)



    @classmethod
    def from_state(cls, name):
        pass

    @classmethod
    def from_location(cls, long, lat):
        return cls(TimezoneFinder().timezone_at(lng = long, lat = lat))

    @property
    def current_time(self):
        return datetime.datetime.now().astimezone(self.tz)
        # return loc_dt.strftime('%H:%M')

    def __str__(self):
        return "Timezone object: name=" + self.name

if __name__ == "__main__":
    timezone = Timezone.from_city("Warsaw")
    print(timezone.country)
