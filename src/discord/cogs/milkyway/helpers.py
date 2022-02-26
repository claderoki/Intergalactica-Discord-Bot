import asyncio
import datetime

import discord
import peewee

import src.config as config
from src.discord import SendableException
from src.models import MilkywaySettings, Milkyway, GuildRewardsProfile
from src.discord.cogs.guildrewards.helpers import GuildRewardsCache, GuildRewardsHelper
from src.discord.helpers import HumanRepository, KnownItem, IntWaiter, StrWaiter, ItemCache, ColorHelper


class MilkywayData:
    __slots__ = ("item_amounts", "profile", "member")

    def __init__(self, item_amounts: dict, profile: GuildRewardsProfile, member: discord.member):
        self.item_amounts = item_amounts
        self.profile = profile
        self.member = member


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
        self.settings = MilkywayCache.get_settings(self.ctx.guild.id)
        self.data = self.__get_data()

    def __pre_validate(self):
        if self.settings is None:
            raise SendableException("Milkyway is not setup for this server yet.")

        currently_active = MilkywayRepository.currently_active(self.ctx.guild.id)
        if currently_active >= self.settings.active_limit:
            raise SendableException(f"There are currently {currently_active} milkyways already active. The limit for "
                                    f"this server is {self.settings.active_limit}.")

        if self.godmode and not self.settings.godmode:
            raise SendableException("Godmode is not enabled for this server.")

        if self.godmode and not self.ctx.author.guild_permissions.administrator:
            raise SendableException("You need to have the administrator permission to be able to use godmode.")

        if not GuildRewardsHelper.is_enabled_for(self.ctx.guild.id):
            raise SendableException("Guild rewards need to be setup/enabled for this server.")

        category: discord.CategoryChannel = self.ctx.bot.get_channel(self.settings.category_id)
        if category is None:
            raise SendableException("The milkyway category seems to be missing. Please have an admin recheck.")

        if not category.permissions_for(self.ctx.guild.me).manage_channels:
            raise SendableException("The bot does not have the `manage_channels` permission for this category.")

    async def create(self) -> Milkyway:
        self.__load()
        self.__pre_validate()
        available_purchases = self.__get_available_purchases()
        available_purchase = await self.__get_available_purchase(available_purchases)
        amount = await self.__ask_for_amount(available_purchase)
        milkyway = self.__get_new_milkyway(available_purchase, amount)

        await milkyway.editor_for(self.ctx, "name")
        await milkyway.editor_for(self.ctx, "description")
        milkyway.save()
        MilkywayHelper.purchase(milkyway, milkyway.amount)
        return milkyway

    async def extend(self, milkyway: Milkyway):
        self.__load()
        self.__pre_validate()
        available_purchases = self.__get_available_purchases()
        available_purchase = self.__get_existing_available_purchase(available_purchases, milkyway)
        amount = await self.__ask_for_amount(available_purchase)
        days_worth = self.__get_days_worth(available_purchase, amount)
        milkyway.amount = self.__get_amount(available_purchase, amount)
        milkyway.total_days += days_worth
        milkyway.expires_at += datetime.timedelta(days=days_worth)
        milkyway.save()
        MilkywayHelper.purchase(milkyway, milkyway.amount)

    def __get_days_worth(self, available_purchase: MilkywayAvailablePurchase, amount: int) -> int:
        if available_purchase.type == KnownItem.milkyway:
            return amount * 7
        return amount

    def __get_amount(self, available_purchase: MilkywayAvailablePurchase, amount: int) -> int:
        if available_purchase.type == "points":
            return amount * self.settings.cost_per_day
        return amount

    def __get_purchase_type(self, available_purchase: MilkywayAvailablePurchase) -> Milkyway.PurchaseType:
        if available_purchase.type in (KnownItem.milkyway, KnownItem.orion_belt):
            return Milkyway.PurchaseType.item
        elif available_purchase.type == "points":
            return Milkyway.PurchaseType.points
        elif self.godmode:
            return Milkyway.PurchaseType.none

    def __get_new_milkyway(self, available_purchase: MilkywayAvailablePurchase, amount: int) -> Milkyway:
        milkyway = Milkyway(
            guild_id=self.ctx.guild.id,
            amount=self.__get_amount(available_purchase, amount),
            user_id=self.ctx.author.id,
            days_pending=self.__get_days_worth(available_purchase, amount),
            identifier=MilkywayCache.get_and_increment_identifier(self.ctx.guild.id),
            purchase_type=self.__get_purchase_type(available_purchase)
        )

        if available_purchase.type in (KnownItem.milkyway, KnownItem.orion_belt):
            milkyway.item = ItemCache.get_id(available_purchase.type)

        return milkyway

    async def __ask_for_amount(self, available_purchase: MilkywayAvailablePurchase) -> int:
        prompt = self.ctx.translate(f"milkyway_type_{available_purchase.type}_amount_prompt")
        waiter = IntWaiter(self.ctx, min=1, max=available_purchase.amount, prompt=prompt)
        return await waiter.wait()

    def __get_existing_available_purchase(self, available_purchases: list, milkyway: Milkyway) -> MilkywayAvailablePurchase:
        if milkyway.purchase_type == Milkyway.PurchaseType.item:
            type = ItemCache.get_code(milkyway.item_id)
            min_needed = 1
        elif milkyway.purchase_type == Milkyway.PurchaseType.points:
            type = milkyway.purchase_type.name
            min_needed = self.settings.cost_per_day
        else:
            type = "days"
            min_needed = None

        for available_purchase in available_purchases:
            if available_purchase.type == type:
                return available_purchase
        raise SendableException(f"You need at least {min_needed} {type} to extend this milkyway.")

    async def __get_available_purchase(self, available_purchases: list) -> MilkywayAvailablePurchase:
        if len(available_purchases) == 0:
            raise SendableException("You are unable to create a milkyway. You do not have any clovers or items.")
        if len(available_purchases) == 1:
            return available_purchases[0]

        prompt = self.ctx.translate("milkyway_purchase_type_prompt")
        allowed_words = [x.type for x in available_purchases]
        waiter = StrWaiter(self.ctx, allowed_words=allowed_words, prompt=prompt)
        selected_purchase_type = await waiter.wait()
        for purchase_type in available_purchases:
            if purchase_type.type == selected_purchase_type:
                return purchase_type

    def __get_available_purchases(self) -> list:
        if self.godmode:
            return [MilkywayAvailablePurchase("days", 999)]

        purchase_types = [MilkywayAvailablePurchase(k, v) for k, v in self.data.item_amounts.items()]

        max_days = self.data.profile.points // self.settings.cost_per_day
        if max_days > 0:
            purchase_types.append(MilkywayAvailablePurchase("points", max_days))
        return purchase_types

    def __get_data(self) -> MilkywayData:
        if self.godmode:
            return MilkywayData({}, None, self.ctx.author)
        profile = GuildRewardsCache.get_profile(self.ctx.author.guild.id, self.ctx.author.id)
        items = [KnownItem.milkyway, KnownItem.orion_belt]
        item_amounts = HumanRepository.get_item_amounts(self.ctx.author.id, items, True)

        return MilkywayData(item_amounts, profile, self.ctx.author)


class MilkywayHelper:

    @classmethod
    async def expire(cls, milkyway: Milkyway):
        settings = MilkywayCache.get_settings(milkyway.guild_id)

        milkyway.status = Milkyway.Status.expired
        channel = milkyway.channel
        if channel is not None:
            try:
                await channel.delete(reason="Expired")
                cls.log(settings, f"Successfully removed expired channel `{channel.name}`")
            except:
                cls.log(settings, f"Unable to remove channel `{channel.name}`")
        milkyway.channel_id = None
        milkyway.save()

    @classmethod
    def log(cls, settings: MilkywaySettings, message: str):
        channel = config.bot.get_channel(settings.log_channel_id)
        asyncio.gather(channel.send(message))

    @classmethod
    def __increase_or_decrease_amount(cls, milkyway: Milkyway, amount: int):
        if milkyway.purchase_type == Milkyway.PurchaseType.item:
            HumanRepository.increment_item(milkyway.user_id, milkyway.item_id, amount)
        elif milkyway.purchase_type == Milkyway.PurchaseType.points:
            profile = GuildRewardsCache.get_profile(milkyway.guild_id, milkyway.user_id)
            profile.points += amount
            profile.save()

    @classmethod
    def purchase(cls, milkyway: Milkyway, amount: int):
        cls.__increase_or_decrease_amount(milkyway, -amount)

    @classmethod
    def giveback(cls, milkyway: Milkyway, amount: int):
        cls.__increase_or_decrease_amount(milkyway, amount)

    @classmethod
    async def accept(cls, milkyway: Milkyway):
        settings = MilkywayCache.get_settings(milkyway.guild_id)
        milkyway.status = Milkyway.Status.accepted
        milkyway.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=milkyway.days_pending)
        channel = await cls.create_channel_for(milkyway, settings.category_id)
        milkyway.channel_id = channel.id
        milkyway.total_days = milkyway.days_pending
        milkyway.days_pending = 0
        milkyway.save()

    @classmethod
    async def deny(cls, milkyway: Milkyway, reason: str):
        milkyway.status = Milkyway.Status.denied
        milkyway.deny_reason = reason
        milkyway.save()
        cls.giveback(milkyway, milkyway.amount)

    @classmethod
    async def create_channel_for(cls, milkyway: Milkyway, category_id: int) -> discord.TextChannel:
        if milkyway.channel_id is not None:
            raise SendableException("This milkyway already has a channel")
        topic = cls.get_channel_topic(milkyway)
        guild = milkyway.guild
        category: discord.CategoryChannel = guild.get_channel(category_id)
        overwrites = category.overwrites
        overwrites[milkyway.member] = discord.PermissionOverwrite(manage_messages=True)

        return await guild.create_text_channel(
            name=milkyway.name,
            topic=topic,
            category=category,
            overwrites=overwrites
        )

    @classmethod
    def get_channel_topic(cls, milkyway: Milkyway) -> str:
        return f"{milkyway.description}. Expires at {milkyway.expires_at}"


class MilkywayUI:
    @classmethod
    def get_pending_embed(cls, milkyway: Milkyway) -> discord.Embed:
        embed = discord.Embed(color=ColorHelper.get_primary_color())
        member = milkyway.member
        embed.set_author(name=str(milkyway.member), icon_url=member.avatar_url)
        lines = [f"A milkyway was requested for {milkyway.days_pending} days", f"Name: `{milkyway.name}`",
                 f"Description: `{milkyway.description}`"]

        embed.description = "\n".join(lines)

        footer = [f"Use '/milkyway deny {milkyway.identifier} <reason>' to deny this request",
                  f"Use '/milkyway accept {milkyway.identifier}' to accept this request"]
        embed.set_footer(text="\n".join(footer))
        return embed

    @classmethod
    def get_denied_embed(cls, milkyway: Milkyway) -> discord.Embed:
        embed = discord.Embed(color=ColorHelper.get_primary_color())
        embed.title = "Milkyway denied"
        embed.description = "Unfortunately, your request for a milkyway channel was denied.\nReason: " + milkyway.deny_reason
        return embed


class MilkywayCache:
    _last_identifiers: dict = {}
    _settings: dict = {}

    @classmethod
    def get_and_increment_identifier(cls, guild_id: int) -> int:
        last_identifier = cls._last_identifiers.get(guild_id)
        if last_identifier is not None:
            cls._last_identifiers[guild_id] += 1
            return last_identifier + 1

        last_identifier = MilkywayRepository.get_increment_identifier(guild_id)
        cls._last_identifiers[guild_id] = last_identifier
        return last_identifier

    @classmethod
    def get_settings(cls, guild_id) -> MilkywaySettings:
        settings = cls._settings.get(guild_id)
        if settings is not None:
            return settings

        settings = MilkywaySettings.get_or_none(guild_id=guild_id)
        if settings is not None:
            cls._settings[guild_id] = settings
            return settings


class MilkywayRepository:
    @classmethod
    def get_increment_identifier(cls, guild_id: int) -> int:
        max_identifier = (Milkyway.select(peewee.fn.MAX(Milkyway.identifier))
                          .where(Milkyway.guild_id == guild_id).scalar())
        return (max_identifier or 0) + 1

    @classmethod
    def get_expired(cls) -> list:
        return list((Milkyway.select(Milkyway.id, Milkyway.guild_id, Milkyway.channel_id, Milkyway.status)
                     .where(Milkyway.expires_at.is_null(False))
                     .where(Milkyway.expires_at <= datetime.datetime.utcnow())
                     ))

    @classmethod
    def currently_active(cls, guild_id: int) -> int:
        return (Milkyway
                .select()
                .where(Milkyway.guild_id == guild_id)
                .where(Milkyway.status == Milkyway.Status.accepted)
                .count())
