import requests

class FixerioException(Exception):
    def __init__(self, code, message):
        self.code    = code
        self.message = message

class BaseCurrencyAccessRestricted(FixerioException):
    code = 105
    type = "base_currency_access_restricted"

class Currency:
    __slots__ = ("code", "name", "value")

    def __init__(self, code, name, value = None):
        self.code  = code
        self.name  = name
        self.value = value

    def __str__(self):
        return f"'code = {self.code}, name = {self.name}, value = {self.value}'"

    def __repr__(self):
        return str(self)

class Api:
    __base_url = "http://data.fixer.io/api"

    def __init__(self, key):
        self.key = key
        self._cache = {}

    def __request(self, endpoint, **kwargs):
        url = f"{self.__base_url}/{endpoint}"
        if "access_key" not in kwargs:
            kwargs["access_key"] = self.key

        for key,value in dict(kwargs).items():
            if value is None:
                del kwargs[key]
            if key == "_from":
                kwargs["from"] = value
                del kwargs[key]

        request = requests.get(url, params = kwargs)
        json = request.json()
        self.__raise_if_unsuccessful(json)
        return json

    def __raise_if_unsuccessful(self, data):
        if not data["success"]:
            raise FixerioException(data["error"]["code"], data["error"].get("info", data["error"].get("type")))

    def symbols(self):
        json = self.__request("symbols")
        symbols = [Currency(k, v) for k,v in json["symbols"].items()]
        self._cache["supported_symbols"] = symbols
        return symbols

    def latest(self, base = None, symbols = None, date = None):
        if not isinstance(symbols, str) and symbols is not None:
            symbols = ",".join(symbols)

        base_default = "EUR"

        kwargs = {}
        kwargs["date"] = date
        kwargs["base"] = base

        if symbols is not None:
            kwargs["symbols"] = symbols

        if base != base_default:
            kwargs["base"] = base_default
            if symbols is not None:
                kwargs["symbols"] = f"{symbols},{base}"
            json = self.__request("latest", **kwargs)
            base_value = json["rates"][base or base_default]
            new_json = {k:v for k, v in json.items() if k in ("success", "timestamp", "date")}
            new_json["base"] = base or base_default

            new_json["rates"] = {}
            for key, value in json["rates"].items():
                if key != base:
                    new_json["rates"][key] = value / base_value

            return new_json
        else:

            json = self.__request("latest", **kwargs)
            return json

    def convert(self, base, to, amount = 1, date = None):
        json = self.latest(base = base, symbols = to, date = date)

        currencies = []
        for key, value in json["rates"].items():
            currencies.append(Currency(key, None, value*amount))
        return currencies
