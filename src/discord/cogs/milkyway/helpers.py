import datetime
from enum import Enum

import discord
from discord.ext import commands

from src.discord import SendableException
from src.models import MilkywaySettings, Milkyway
from .validator import MilkywayData
from src.discord.cogs.guildrewards.helpers import GuildRewardsCache, GuildRewardsHelper
from src.discord.helpers import HumanRepository, KnownItem, IntWaiter, StrWaiter, ItemCache, TimeDeltaWaiter


class MilkywayAvailablePurchase:
    __slots__ = ("type", "amount")

    def __init__(self, type: str, amount: int):
        self.type = type
        self.amount = amount


class MilkywayProcessor:
    data: MilkywayData
    settings: MilkywaySettings

    __slots__ = ("ctx", "godmode", "settings", "data")

    def __init__(self, ctx, godmode: bool):
        self.godmode = godmode
        self.ctx = ctx

    def __load(self):
        self.settings = MilkywaySettings.get_or_none(guild_id=self.ctx.guild.id)
        self.data = self.__get_data()

    def __pre_validate(self):
        if self.settings is None:
            raise SendableException("Milkyway is not setup for this server yet.")

        if self.godmode and not self.settings.godmode:
            raise SendableException("Godmode is not enabled for this server.")

        if self.godmode and not self.ctx.author.guild_permissions.administrator:
            raise SendableException("You need to have the administrator permission to be able to use godmode.")

        if not GuildRewardsHelper.is_enabled_for(self.ctx.guild.id):
            raise SendableException("Guild rewards need to be setup/enabled for this server.")

    async def create(self) -> Milkyway:
        self.__load()
        self.__pre_validate()
        available_purchases = self.__get_available_purchases()
        available_purchase = await self.__get_available_purchase(available_purchases)
        amount = await self.__ask_for_amount(available_purchase)
        milkyway = self.__get_new_milkyway(available_purchase, amount)

        return milkyway

    def __get_new_milkyway(self, available_purchase: MilkywayAvailablePurchase, amount: int) -> Milkyway:
        milkyway = Milkyway(guild_id = self.ctx.guild.id, amount = amount)
        milkyway.days_pending = amount

        if available_purchase.type == KnownItem.milkyway:
            milkyway.days_pending *= 7

        if available_purchase.type in (KnownItem.milkyway, KnownItem.orion_belt):
            milkyway.item = ItemCache.get_id(available_purchase.type)
            milkyway.purchase_type = Milkyway.PurchaseType.item
        elif available_purchase.type == "points":
            milkyway.purchase_type = Milkyway.PurchaseType.points
        elif self.godmode:
            milkyway.purchase_type = Milkyway.PurchaseType.none

        return milkyway

    async def __ask_for_amount(self, available_purchase: MilkywayAvailablePurchase) -> int:
        prompt = self.ctx.translate(f"milkyway_type_{available_purchase.type}_amount_prompt")
        waiter = IntWaiter(self.ctx, min=1, max=available_purchase.amount, prompt=prompt)
        return await waiter.wait()

    async def __get_available_purchase(self, purchase_types: list) -> MilkywayAvailablePurchase:
        if len(purchase_types) == 0:
            raise SendableException("You are unable to create a milkyway. You do not have any clovers or items.")
        if len(purchase_types) == 1:
            return purchase_types[0]

        prompt = self.ctx.translate("milkyway_purchase_type_prompt")
        allowed_words = [x.type for x in purchase_types]
        waiter = StrWaiter(self.ctx, allowed_words=allowed_words, prompt=prompt)
        selected_purchase_type = await waiter.wait()
        for purchase_type in purchase_types:
            if purchase_type.type == selected_purchase_type:
                return purchase_type

    def __get_available_purchases(self) -> list:
        if self.godmode:
            return [MilkywayAvailablePurchase("days", None)]

        purchase_types = [MilkywayAvailablePurchase(k, v) for k, v in self.data.item_amounts.items()]

        max_days = self.data.profile.points // self.settings.cost_per_day
        if max_days > 0:
            purchase_types.append(MilkywayAvailablePurchase("points", max_days))
        return purchase_types

    def __get_data(self) -> MilkywayData:
        if self.godmode:
            return MilkywayData({}, None, self.ctx.author)
        profile = GuildRewardsCache.get_profile(self.ctx.author.guild.id, self.ctx.author.id)
        item_amounts = HumanRepository.get_item_amounts(self.ctx.author.id, [KnownItem.milkyway, KnownItem.orion_belt],
                                                        True)
        return MilkywayData(item_amounts, profile, self.ctx.author)


class MilkywayHelper:
    @classmethod
    async def __ask_for_amount(cls, ctx: commands.Context, type: str, available: int) -> int:
        waiter = IntWaiter(ctx, min=1, max=available, prompt=ctx.translate(f"milkyway_type_{type}_amount_prompt"))
        return await waiter.wait()


class MilkywayRepository:
    pass
