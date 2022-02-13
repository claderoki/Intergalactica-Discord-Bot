import json

from .api.base import ApiCall


class HueBridgeCall(ApiCall):
    __slots__ = ("username",)

    ip = None
    last_username = None

    def raise_on_error(self, response: dict):
        if isinstance(response, list) and len(response) > 0:
            first = response[0]
            if "error" in first:
                error = first["error"]
                raise Exception(error["description"])

    @classmethod
    def set_ip(cls, ip):
        cls.ip = ip

    def __init__(self, username=None):
        self.username = username

    def get_base_uri(self) -> str:
        return f"http://{self.ip}/api"


class Cache:
    __slots__ = ()

    base_folder = "data/"

    @classmethod
    def set(cls, key, value):
        with open(f"{cls.base_folder}/{key}", "w") as f:
            f.write(str(value))

    @classmethod
    def get(cls, key):
        try:
            with open(f"{cls.base_folder}/{key}") as f:
                value = f.read()
                if value:
                    return value
        except FileNotFoundError:
            return None


class HueBridgeCache(Cache):

    @classmethod
    def get_username(cls) -> str:
        return cls.get("hue_bridge_username")

    @classmethod
    def set_username(cls, username: str):
        return cls.set("hue_bridge_username", username)

    @classmethod
    def get_last_known_state(cls) -> str:
        last = cls.get("hue_bridge_last_known_state")
        if last is not None:
            return json.loads(last)

    @classmethod
    def set_last_known_state(cls, last_known_state):
        return cls.set("hue_bridge_last_known_state", json.dumps(last_known_state.to_dict()))
