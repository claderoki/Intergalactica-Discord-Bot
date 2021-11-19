import datetime
import asyncio

from discord.ext import tasks, commands

from src.discord.helpers.converters import EnumConverter
from src.discord.cogs.intergalactica import Intergalactica
from src.discord.helpers.paginating import Paginator
from .helpers import SecretSantaHelper, SecretSantaRepository, SecretSantaUI
from src.discord.helpers.waiters.base import DateWaiter, TimeWaiter
from src.discord.errors.base import SendableException
from src.discord.helpers.known_guilds import KnownGuild
from src.models import SecretSantaParticipant, SecretSanta, database
from src.discord.cogs.core import BaseCog
import src.config as config

class SecretSantaCog(BaseCog, name = "Secret Santa"):
    _secret_santa_in_progress = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.poller, check = not self.bot.production)

    @commands.group(name = "secretsanta")
    async def secret_santa(self, _):
        pass

    @secret_santa.command(name = "help")
    async def secret_santa_help(self, ctx):
        """Shows this embed."""
        embed = SecretSantaUI.get_help_embed(ctx.prefix)
        paginator = Paginator.from_embed(ctx, embed, max_fields = 10)
        await paginator.wait()

    @secret_santa.command(name = "view")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    async def secret_santa_view(self, ctx, type: EnumConverter(SecretSantaParticipant.Type)):
        """View a list of participants (Admin only)."""
        now          = datetime.datetime.utcnow()
        secret_santa = SecretSantaRepository.get(guild_id = ctx.guild.id, year = now.year)
        participants = SecretSantaRepository.get_participants(secret_santa.id, type)

        lines = []
        for participant in participants:
            lines.append(str(participant.user))
        await ctx.send("\n".join(lines))

    @secret_santa.command(name = "setup")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    async def secret_santa_setup(self, ctx):
        """Manage this servers secret santa this year (Admin only)."""
        if ctx.guild.id != KnownGuild.intergalactica:
            raise SendableException("Not supported yet for other guilds.")
        now = datetime.datetime.utcnow()

        secret_santa = SecretSantaRepository.get(guild_id = ctx.guild.id, year = now.year)
        new = secret_santa is None

        if new:
            secret_santa = SecretSanta(guild_id = ctx.guild.id, active = True)

        date = await DateWaiter(ctx, prompt = "What date should this event start?").wait()
        time = await TimeWaiter(ctx, prompt = "What time should this event start?").wait()

        secret_santa.start_date = datetime.datetime.combine(date = date, time = time)

        secret_santa.save()
        await ctx.success("Secret santa has been setup for this server.")

    @secret_santa.command(name = "delete")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    async def secret_santa_delete(self, ctx):
        """Delete this servers secret santa this year (Admin only)."""
        now = datetime.datetime.utcnow()

        secret_santa = SecretSantaRepository.get(guild_id = ctx.guild.id, year = now.year)
        if secret_santa is not None:
            secret_santa.delete_instance()
        await ctx.success("Secret santa has been removed for this server.")

    @secret_santa.command(name = "create")
    @commands.dm_only()
    async def secret_santa_create(self, ctx):
        """Create your secret santa profile."""
        secret_santa = await SecretSantaHelper.get_secret_santa(ctx)
        if secret_santa.started_at is not None:
            raise SendableException("Unfortunately this event has already started.")

        query = (SecretSantaParticipant
            .select(SecretSantaParticipant.type)
            .where(SecretSantaParticipant.user_id == ctx.author.id)
            .where(SecretSantaParticipant.secret_santa == secret_santa))

        available_types = [x for x in SecretSantaParticipant.Type if x not in [x.type for x in query]]

        if secret_santa.guild_id == KnownGuild.intergalactica:
            member = secret_santa.guild.get_member(ctx.author.id)
            if secret_santa.guild.get_role(Intergalactica._role_ids["5k+"]) not in member.roles:
                raise SendableException("You need the 5k+ role to participate.")
            if secret_santa.guild.get_role(Intergalactica._role_ids["selfies"]) not in member.roles:
                available_types.remove(SecretSantaParticipant.Type.monetary)

        if len(available_types) == 0:
            raise SendableException("Nothing available.")

        participant = SecretSantaParticipant(user_id = ctx.author.id, secret_santa = secret_santa)
        await participant.editor_for(ctx, "type", properties_to_skip = [x for x in SecretSantaParticipant.Type if x not in available_types])

        description_key = f"secret_santa_participant_{participant.type.name}_description_prompt"
        await participant.editor_for(ctx, "description", prompt = ctx.translate(description_key))

        participant.save()
        await ctx.success("Your secret santa profile has been created.")

    @secret_santa.command(name = "edit")
    @commands.dm_only()
    async def secret_santa_edit(self, ctx, type: EnumConverter(SecretSantaParticipant.Type)):
        """Edit your secret santa profile."""
        secret_santa = await SecretSantaHelper.get_secret_santa(ctx)
        if secret_santa.started_at is not None:
            raise SendableException("Unfortunately this event has already started.")

        participant = SecretSantaRepository.get_participant(secret_santa.id, ctx.author.id, type)

        if participant is None:
            raise SendableException("Create it first.")

        description_key = f"secret_santa_participant_{participant.type.name}_description_prompt"
        await participant.editor_for(ctx, "description", prompt = ctx.translate(description_key))

        participant.save()
        await ctx.success("Your secret santa profile has been setup.")

    @secret_santa.command(name = "dropout")
    @commands.dm_only()
    async def secret_santa_dropout(self, ctx, type: EnumConverter(SecretSantaParticipant.Type)):
        """Dropout from participating in the secret santa event this year."""
        secret_santa = await SecretSantaHelper.get_secret_santa(ctx)
        participant  = SecretSantaRepository.get_participant(secret_santa.id, ctx.author.id, type)
        if participant is None:
            raise SendableException("You weren't participating yet.")
        if participant.giftee is not None or secret_santa.started_at is not None:
            raise SendableException("Unable to drop out at this stage (already started)")

        participant.delete_instance()
        await ctx.success("You successfully dropped out of the secret santa event.")

    @tasks.loop(seconds = 120)
    async def poller(self):
        if self.bot.owner is None:
            return

        if self._secret_santa_in_progress:
            return

        print("----Secret Santa Assignments----")

        self._secret_santa_in_progress = True
        for secret_santa in SecretSantaRepository.get_queue():
            await process_secret_santa_queue(secret_santa)

        self._secret_santa_in_progress = False

async def process_secret_santa_queue(secret_santa: SecretSanta):
    participants = SecretSantaHelper.get_filtered_participants(secret_santa)
    log = []
    with database.atomic() as transaction:
        tasks = []
        secret_santa.started_at = datetime.datetime.utcnow()
        secret_santa.save()

        secret_santas = {}

        for type in participants:
            available_participants = [x for x in participants[type]]

            for participant in participants[type]:
                for _ in range(3):
                    try:
                        giftee = SecretSantaHelper.get_random_giftee(participant, available_participants)
                    except Exception:
                        transaction.rollback()
                        return
                    if giftee.user_id not in secret_santas.get(giftee.user_id, []) and giftee.user_id not in secret_santas.get(participant.user_id, []):
                        break

                secret_santas.setdefault(participant.user_id, []).append(giftee.user_id)
                secret_santas.setdefault(giftee.user_id, []).append(participant.user_id)

                available_participants.remove(giftee)
                embed  = SecretSantaUI.get_giftee_info_embed(giftee)
                tasks.append(participant.user.send(embed = embed))
                participant.giftee = giftee
                participant.save()

        asyncio.gather(*tasks)
        transaction.commit()

def setup(bot):
    bot.add_cog(SecretSantaCog(bot))
