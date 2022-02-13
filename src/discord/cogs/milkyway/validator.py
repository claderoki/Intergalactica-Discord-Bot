import discord

from src.models import Milkyway, MilkywaySettings, GuildRewardsProfile


#
#
# class MilkywayValidationResult:
#     __slots__ = ("errors", "available_purchase_types")
#
#     def __init__(self):
#         self.errors = []
#         self.available_purchase_types = []
#
#     def add_error(self, message: str):
#         self.errors.append(message)
#
#     def add_purchase_type(self, purchase_type: Milkyway.PurchaseType):
#         self.available_purchase_types.append(purchase_type)
#
#     def is_success(self) -> bool:
#         return len(self.errors) == 0
#

class MilkywayData:
    __slots__ = ("item_amounts", "profile", "member")

    def __init__(self, item_amounts: dict, profile: GuildRewardsProfile, member: discord.member):
        self.item_amounts = item_amounts
        self.profile = profile
        self.member = member
#
#
# class MilkywayValidator:
#     __slots__ = ("settings", "godmode", "data")
#
#     def __init__(self, settings: MilkywaySettings, godmode: bool, data: MilkywayData):
#         self.settings = settings
#         self.godmode = godmode
#         self.data = data
#
#     def __validate_godmode(self, result: MilkywayValidationResult) -> MilkywayValidationResult:
#         if not self.data.member.guild_permissions.administrator:
#             result.add_error("You need to have the administrator permission to be able to use godmode.")
#
#         if not self.settings.godmode:
#             result.add_error("Godmode is not enabled for this server.")
#
#         return result
#
#     def validate(self, days: int = 7) -> MilkywayValidationResult:
#         result = MilkywayValidationResult()
#
#         if self.godmode:
#             return self.__validate_godmode(result)
#
#         return result
