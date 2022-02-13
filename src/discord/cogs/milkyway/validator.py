import discord

from src.models import Milkyway, MilkywaySettings


class MilkywayValidationResult:
    __slots__ = ("errors", "available_purchase_types")

    def __init__(self):
        self.errors = []
        self.available_purchase_types = []

    def add_error(self, message: str):
        self.errors.append(message)

    def add_purchase_type(self, purchase_type: Milkyway.PurchaseType):
        self.available_purchase_types.append(purchase_type)

    def is_success(self) -> bool:
        return len(self.errors) == 0


class MilkywayValidator:
    __slots__ = ("member", "settings", "godmode")

    def __init__(self, member: discord.Member, settings: MilkywaySettings, godmode: bool):
        self.member = member
        self.settings = settings
        self.godmode = godmode

    def validate(self) -> MilkywayValidationResult:
        result = MilkywayValidationResult()
        if self.godmode:
            result.add_purchase_type(Milkyway.PurchaseType.none)
            return result

        return result
