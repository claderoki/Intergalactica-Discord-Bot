
class WeatherInfo:
    __slots__ = ("id", "main", "description", "icon", "icon_url", "city")

    def __init__(self, city, data):
        self.city = city
        self.__init_data(data)

    def __init_data(self, data):
        self.id = data["id"]
        self.main = data["main"]
        self.description = data["description"]
        self.icon = data["icon"]

        self.icon_url = f"https://openweathermap.org/img/wn/{self.icon}@2x.png"

    @property
    def emoji(self):
        return \
        {
            "Rain"         : "🌧",
            "Snow"         : "🌨",
            "Clear"        : "☀",
            "Clouds"       : "☁",
            "Thunderstorm" : "⛈",
            "Fog"          : "🌫️",
            "Smoke"        : "💨",
            "Drizzle"      : "🌧",
            "Mist"         : "🌫️"
        }[self.main]