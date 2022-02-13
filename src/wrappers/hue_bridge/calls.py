from .api.base import HttpMethod
from .base import HueBridgeCall
from .responses import Light, LightState


class AuthenticateCall(HueBridgeCall):
    __slots__ = ("device_type",)

    def __init__(self, device_type: str):
        self.device_type = device_type

    @classmethod
    def get_method(cls) -> HttpMethod:
        return HttpMethod.post

    def get_payload(self) -> dict:
        return {"devicetype": self.device_type}

    def parse_response(self, response: dict) -> str:
        return response[0]["success"]["username"]


class GetLightsCall(HueBridgeCall):
    __slots__ = ()

    def get_full_uri(self) -> str:
        return f"{self.get_base_uri()}/{self.username}/lights"

    def parse_response(self, response: dict):
        lights = []
        for id, data in response.items():
            state = LightState(
                data["state"]["on"],
                data["state"]["bri"],
                data["state"]["alert"],
                data["state"]["mode"],
                data["state"]["reachable"]
            )
            lights.append(Light(id, state, data["name"]))
        return lights


class GetLightCall(HueBridgeCall):
    __slots__ = ("id",)

    def __init__(self, username: str, id: int):
        super().__init__(username)
        self.id = id

    def get_full_uri(self) -> str:
        return f"{self.get_base_uri()}/{self.username}/lights/{self.id}"

    def parse_response(self, response: dict):
        state = LightState(
            response["state"]["on"],
            response["state"]["bri"],
            response["state"]["alert"],
            response["state"]["mode"],
            response["state"]["reachable"]
        )
        return Light(self.id, state, response["name"])


class UpdateLightCall(HueBridgeCall):
    __slots__ = ("id", "state")

    def __init__(self, username: str, id: int, state: LightState):
        super().__init__(username)
        self.id = id
        self.state = state

    def get_method(self):
        return HttpMethod.put

    def get_payload(self):
        return self.state.to_dict()

    def get_full_uri(self) -> str:
        return f"{self.get_base_uri()}/{self.username}/lights/{self.id}/state"
