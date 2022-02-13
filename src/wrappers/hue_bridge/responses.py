class Response:
    __slots__ = ()

    def __str__(self):
        return ", ".join(f"{x} => {getattr(self, x)}" for x in self.__slots__)

    def to_dict(self, options: list = None) -> dict:
        if options is None:
            options = self.__slots__
        return {x: getattr(self, x) for x in options}


class LightState(Response):
    __slots__ = ("on", "brightness", "alert", "mode", "reachable")

    def __init__(self, on: bool, brightness: int, alert: str, mode: str, reachable: bool):
        self.on = on
        self.brightness = brightness
        self.alert = alert
        self.mode = mode
        self.reachable = reachable

    def to_dict(self) -> dict:
        dictionary = super().to_dict(("brightness", "on"))
        dictionary["bri"] = dictionary["brightness"]
        del dictionary["brightness"]
        return dictionary


class Light(Response):
    __slots__ = ("id", "state", "name")

    def __init__(self, id: int, state: LightState, name: str):
        self.id = id
        self.state = state
        self.name = name
