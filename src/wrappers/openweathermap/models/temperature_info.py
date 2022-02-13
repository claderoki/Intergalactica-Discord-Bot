class TemperatureInfo:
    __slots__ = ("temperature", "feels_like", "pressure",
                 "humidity", "minimum_temperature", "maximum_temperature",
                 "sea_level", "ground_level", "city")

    def __init__(self, city, data):
        self.city = city
        self.__init_data(data)

    def __init_data(self, data):
        self.temperature = data["temp"]
        self.feels_like = data["feels_like"]
        self.pressure = data["pressure"]
        self.humidity = data["humidity"]
        self.minimum_temperature = data["temp_min"]
        self.maximum_temperature = data["temp_max"]
        self.sea_level = data.get("sea_level")
        self.ground_level = data.get("grnd_level")

    def __str__(self):
        return "TemperatureInfo object: Temperature=" + self.temperature
