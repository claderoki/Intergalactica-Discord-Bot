import datetime
import random

from src.models import GuildRewardsSettings, GuildRewardsProfile


class GuildRewardsRepository:
    @classmethod
    def get_settings(cls, guild_id: int) -> GuildRewardsSettings:
        return GuildRewardsSettings.get_or_none(guild_id=guild_id)

    @classmethod
    def get_profile(cls, guild_id: int, user_id: int) -> GuildRewardsProfile:
        return GuildRewardsProfile.get_or_none(guild_id=guild_id, user_id=user_id)

    @classmethod
    def create_profile(cls, guild_id: int, user_id: int) -> GuildRewardsProfile:
        return GuildRewardsProfile.create(guild_id=guild_id, user_id=user_id)


class GuildRewardsHelper:
    _last_payouts = {}

    @classmethod
    def __calculate_points(cls, settings: GuildRewardsSettings) -> int:
        if settings.min_points_per_message == settings.max_points_per_message:
            return settings.min_points_per_message
        else:
            return random.randint(settings.min_points_per_message, settings.max_points_per_message)

    @classmethod
    def reward(cls, profile: GuildRewardsProfile, settings: GuildRewardsSettings):
        guild_payouts = cls._last_payouts.setdefault(profile.guild_id, {})
        profile.points += cls.__calculate_points(settings)
        profile.save()
        guild_payouts[profile.user_id] = datetime.datetime.utcnow()

    @classmethod
    def has_reward_available(cls, profile: GuildRewardsProfile, settings: GuildRewardsSettings) -> bool:
        guild_payouts = cls._last_payouts.get(profile.guild_id)
        if guild_payouts is None:
            return True

        paid_at: datetime.datetime = guild_payouts.get(profile.user_id)
        if paid_at is None:
            return True
        available_at = paid_at + settings.timeout
        now = datetime.datetime.utcnow()
        return now >= available_at


class GuildRewardsCache:
    _settings = {}
    _profiles = {}

    @classmethod
    def get_settings(cls, guild_id: int) -> GuildRewardsSettings:
        cached = cls._settings.get(guild_id)
        if cached is not None:
            return cached

        uncached = GuildRewardsRepository.get_settings(guild_id=guild_id)
        if uncached is not None:
            cls._settings[guild_id] = uncached
        return uncached

    @classmethod
    def get_profile(cls, guild_id: int, user_id: int) -> GuildRewardsProfile:
        profiles = cls._profiles.setdefault(guild_id, {})

        cached = profiles.get(user_id)
        if cached is not None:
            return cached

        uncached = GuildRewardsRepository.get_profile(guild_id, user_id)
        if uncached is not None:
            profiles[user_id] = uncached
        else:
            GuildRewardsRepository.create_profile(guild_id, user_id)
            return cls.get_profile(guild_id, user_id)
        return uncached
