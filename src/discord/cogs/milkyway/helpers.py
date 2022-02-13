from discord.ext import commands

from discord.ext import commands

from src.discord import SendableException
from src.models import MilkywaySettings
from .validator import MilkywayValidator


class MilkywayHelper:
    __slots__ = ()

    @classmethod
    async def create_milkyway(cls, ctx: commands.Context, godmode: bool):
        settings = MilkywaySettings.get_or_none(guild_id=ctx.guild.id)

        if settings is None:
            raise SendableException(
                "Milkyway is not setup for this server yet. Please ask an admin to set it up first.")

        validator = MilkywayValidator(ctx.author, settings, godmode)
        result = validator.validate()
        if not result.is_success():
            raise SendableException("You are unable to create a milkyway, reason(s): " + ("\n".join(result.errors)))

        print(result)


class MilkywayRepository:
    __slots__ = ()
