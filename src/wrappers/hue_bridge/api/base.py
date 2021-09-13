from enum import Enum
import requests

class HttpMethod(Enum):
    get  = 1
    post = 2
    put  = 3

class ApiCall:
    __slots__ = ()

    @classmethod
    def get_method(cls) -> HttpMethod:
        return HttpMethod.get

    def get_full_uri(self) -> str:
        return self.get_base_uri()

    def get_params(self):
        return None

    def get_payload(self):
        return None

    def call(self):
        uri     = self.get_full_uri()
        params  = self.get_params()
        payload = self.get_payload()

        kwargs = {}
        if payload and len(payload) > 0:
            kwargs["json"] = payload
        elif params and len(params) > 0:
            kwargs["params"] = params

        method = self.get_method()
        if method == HttpMethod.post:
            req = requests.post(uri, **kwargs)
        elif method == HttpMethod.get:
            req = requests.get(uri, **kwargs)
        elif method == HttpMethod.put:
            req = requests.put(uri, **kwargs)

        req.raise_for_status()

        response = req.json()
        self.raise_on_error(response)
        return self.parse_response(response)

    def raise_on_error(self, response: dict):
        pass

    def parse_response(self, response: dict):
        return response
