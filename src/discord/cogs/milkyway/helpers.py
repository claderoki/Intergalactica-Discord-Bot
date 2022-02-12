from enum import Enum

import discord
from discord.ext import commands

import src.config as config
from src.discord import SendableException
from src.discord.cogs.core import BaseCog
from .validator import MilkywayValidator
from src.models import Milkyway, MilkywaySettings

class MilkywayHelper:
    __slots__ = ()

    @classmethod
    async def create_milkyway(cls, ctx: commands.Context, godmode: bool):
        settings = MilkywaySettings.get_or_none(guild_id = ctx.guild.id)

        if settings is None:
            raise SendableException("Milkyway is not setup for this server yet. Please ask an admin to set it up first.")

        validator = MilkywayValidator(ctx.author, settings, godmode)
        result    = validator.validate()
        if not result.is_success():
            raise SendableException("You are unable to create a milkyway, reason(s): " + ("\n".join(result.errors)))

        print(result)

class MilkywayRepository:
    __slots__ = ()
