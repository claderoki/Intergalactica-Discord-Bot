import random
import discord
import datetime

from src.discord.errors.base import SendableException
from src.discord.helpers.known_guilds import KnownGuild
from src.models.secretsanta import SecretSanta, SecretSantaParticipant
import src.config as config

class SecretSantaUI:
    __slots__ = ()

    @classmethod
    def get_base_embed(cls, info: str) -> discord.Embed:
        icon_url = "https://cdn.discordapp.com/attachments/744172199770062899/911012466899689522/ss.png"
        embed = discord.Embed(color = config.bot.get_dominant_color())
        embed.set_author(name = f"Secret Santa ({info})", icon_url = icon_url)
        return embed

    @classmethod
    def get_giftee_info_embed(cls, participant: SecretSantaParticipant) -> discord.Embed:
        embed = cls.get_base_embed(participant.type.value)
        embed.description = f"You are <@{participant.user_id}>'s secret santa! ({participant.user})\n"

        if participant.type == SecretSantaParticipant.Type.monetary:
            field_name = "Wishlist"
        else:
            field_name = "Description"

        embed.add_field(name = field_name, value = participant.description, inline = False)

        return embed

    @classmethod
    def get_help_embed(cls) -> discord.Embed:
        embed = cls.get_base_embed("Commands")

        for command in config.bot.get_command("secretsanta").walk_commands():
            embed.add_field(**command_to_field("/", command))

        return embed

def command_to_field(prefix, command, description = None):
    desc = command.callback.__doc__

    kwargs = {}
    kwargs["value"] = f"`{prefix}{command.qualified_name}`"
    if description is None:
        kwargs["name"] = desc
    else:
        kwargs["value"] += f"\n{desc}{config.br}"
    kwargs["inline"] = False
    return kwargs


class SecretSantaHelper:
    __slots__ = ()

    @classmethod
    def get_filtered_participants(cls, secret_santa: SecretSanta) -> dict:
        participants = {x.name: [] for x in SecretSantaParticipant.Type}

        for participant in secret_santa.participants:
            type = participant.type.name
            user = participant.user
            member = secret_santa.guild.get_member(participant.user_id)
            if user is None or member is None:
                continue
            participants[type].append(participant)

        return participants

    @classmethod
    def get_random_giftee(cls, available_participants: list, participant: SecretSantaParticipant) -> SecretSantaParticipant:
        giftee = random.choice(available_participants)
        if giftee.id == participant.id:
            if len(available_participants) == 1:
                raise Exception("No available participants left.")

            return cls.get_random_giftee(available_participants, participant)
        return giftee

    @classmethod
    async def get_secret_santa(cls, ctx) -> list:
        guilds = SecretSantaRepository.get_available_guilds()

        if len(guilds) == 0:
            raise SendableException("No guilds found.")
        elif len(guilds) == 1:
            guild = ctx.bot.get_guild(guilds[0])
        else:
            raise SendableException("Ask for multiple guild support.")

        member = guild.get_member(ctx.author.id)
        if member is None:
            raise SendableException("Did not find you in the server.")
        
        return SecretSantaRepository.get(guild_id = guild.id, year = datetime.datetime.utcnow().year)


class SecretSantaRepository:
    __slots__ = ()

    @classmethod
    def get_available_guilds(cls) -> list:
        return (KnownGuild.intergalactica, )
        # return tuple([x.guild_id for x in SecretSanta.select(SecretSanta.guild_id).where(SecretSanta.active == True)])

    @classmethod
    def get_queue(cls) -> list:
        return (SecretSanta
            .select()
            .where(SecretSanta.start_date <= datetime.datetime.utcnow())
            .where(SecretSanta.active == True)
            .where(SecretSanta.started_at == None))

    @classmethod
    def get_participants(cls, secret_santa_id: int, type: SecretSantaParticipant.Type) -> list:
        return (SecretSantaParticipant
                .select(SecretSantaParticipant.user_id)
                .where(SecretSantaParticipant.secret_santa == secret_santa_id)
                .where(SecretSantaParticipant.type == type.name))

    @classmethod
    def get(cls, guild_id: int, year: int) -> SecretSanta:
        return (SecretSanta
            .select()
            .where(SecretSanta.guild_id == guild_id)
            .where(SecretSanta.start_date.year == year)
            .first())

    @classmethod
    def get_participant(cls, secret_santa_id: int, user_id: int) -> SecretSantaParticipant:
        return (SecretSantaParticipant
            .select()
            .where(SecretSantaParticipant.user_id == user_id)
            .where(SecretSantaParticipant.secret_santa == secret_santa_id)
            .first())
