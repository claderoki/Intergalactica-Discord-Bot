from src.models import Human, database

class BaseGame:
    def __init__(self, players, ui, bet):
        self.players = players
        self.ui = ui
        self.bet = bet

    def __init_subclass__(cls):
        assert hasattr(cls, "start")
        assert hasattr(cls, "stop")

class BaseUi:
    pass

class DiscordUi(BaseUi):
    pass

class BasePlayer:
    def __init__(self, identity):
        self.identity = identity

class BaseIdentity:
    def __init_subclass__(cls):
        assert hasattr(cls, "add_points")
        assert hasattr(cls, "remove_points")

class AiIdentity(BaseIdentity):
    def __init__(self, name = None):
        self.name = name

    def __str__(self):
        return str(self.name)

    def add_points(self, points):
        pass

    def remove_points(self, points):
        pass

class DiscordIdentity(BaseIdentity):
    def __init__(self, member):
        self.member = member

    def __str__(self):
        return self.member.name

    def add_points(self, points):
        with database.connection_context():
            human, _ = Human.get_or_create(user_id = self.member.id)
            human.gold += points
            human.save()

    def remove_points(self, points):
        with database.connection_context():
            human, _ = Human.get_or_create(user_id = self.member.id)
            human.gold -= points
            human.save()

