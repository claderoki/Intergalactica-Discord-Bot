import os

class EnvironmentalVariables(dict):
    required = (
        "mysql_user",
        "mysql_password",
        "mysql_port",
        "mysql_host",
        "discord_token",
        "owm_key",
        "reddit_client_id",
        "reddit_client_secret",
        "reddit_user_agent"
    )

    def __init__(self, data):
        self.__validate(data)
        super().__init__(data)

    def __getattr__(self, name):
        return self[name]

    def __validate(self, data):
        missing = [x for x in self.required]
        for attr, value in data.items():
            if attr in self.required and value != "":
                missing.remove(attr)

        if len(missing) > 0:
            raise Exception("\n".join(missing))

    @classmethod
    def from_path(cls, path):
        with open(path) as f:
            return cls(dict(x.split("=") for x in f.read().splitlines()))

    @classmethod
    def create_env_file(cls, path):
        lines = [f"{x}=" for x in cls.required]
        with open(path, "w") as f:
            f.write("\n".join(lines))

    def __str__(self):
        return f"{self.__class__.__name__} object"

    @classmethod
    def from_environ(cls):
        return cls(os.environ)

if __name__ == "__main__":
    path = "C:/Users/Clark/Projects/Intergalactica-Discord-Bot/env2"
    try:
        variables = EnvironmentalVariables.from_path(path)
    except FileNotFoundError:
        EnvironmentalVariables.create_env_file(path)

    print(variables)