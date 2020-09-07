from enum import Enum

class TemperatureUnit(Enum):
    Celsius    = "metric"
    Fahrenheit = "imperial"
    Kelvin     = ""

    @property
    def symbol(self):
        if self == self.Celsius:
            return "°C"
        elif self == self.Fahrenheit:
            return "°F"
        elif self == self.Kelvin:
            return "K"
