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


class InMemoryCache:
    _data = {}

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value

    @classmethod
    def get(cls, key):
        return cls._data.get(key)


class HueBridgeCache(InMemoryCache):
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
