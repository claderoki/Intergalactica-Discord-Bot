import datetime
import asyncio

from discord.ext import tasks, commands

from src.discord.cogs.intergalactica import Intergalactica
from src.discord.helpers.paginating import Paginator
from .helpers import SecretSantaHelper, SecretSantaRepository, SecretSantaUI
from src.discord.helpers.waiters.base import DateWaiter, TimeWaiter
from src.discord.errors.base import SendableException
from src.discord.helpers.known_guilds import KnownGuild
from src.models import SecretSantaParticipant, SecretSanta
from src.discord.cogs.core import BaseCog

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
        embed = SecretSantaUI.get_help_embed()
        paginator = Paginator.from_embed(ctx, embed, max_fields = 10)
        await paginator.wait()

    @secret_santa.command(name = "setup")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    async def secret_santa_setup(self, ctx):
        """Manage this servers secret santa this year (admin only)."""
        if ctx.guild.id != KnownGuild.intergalactica:
            raise SendableException("Not supported yet for other guilds.")
        now = datetime.datetime.utcnow()

        secret_santa = SecretSantaRepository.get(guild_id = ctx.guild.id, year = now.year)
        new = secret_santa is None

        if new:
            secret_santa = SecretSanta(guild_id = ctx.guild.id, active = True)

        date = await DateWaiter(ctx, after = now.date(), prompt = "What date should this event start?").wait()
        time = await TimeWaiter(ctx, after = now.time(), prompt = "What time should this event start?").wait()

        secret_santa.start_date = datetime.datetime.combine(date = date, time = time)

        secret_santa.save()
        await ctx.success("Secret santa has been setup for this server.")

    @secret_santa.command(name = "profile")
    @commands.dm_only()
    async def secret_santa_profile(self, ctx):
        """Manage your secret santa profile."""
        secret_santa = await SecretSantaHelper.get_secret_santa(ctx)
        if secret_santa.started_at is not None:
            raise SendableException("Unfortunately this event has already started.")

        participant = SecretSantaRepository.get_participant(secret_santa_id = secret_santa.id, user_id = ctx.author.id)

        new = participant is None
        if new:
            participant = SecretSantaParticipant(user_id = ctx.author.id, secret_santa = secret_santa)
        
        properties_to_skip = []
        if secret_santa.guild_id == KnownGuild.intergalactica:
            guild  = secret_santa.guild
            member = guild.get_member(participant.user_id)
            if guild.get_role(Intergalactica._role_ids["5k+"]) not in member.roles:
                raise SendableException("You need the 5k+ role to participate.")
            if guild.get_role(Intergalactica._role_ids["selfies"]) not in member.roles:
                properties_to_skip.append(SecretSantaParticipant.Type.monetary)

        await participant.editor_for(ctx, "type", properties_to_skip = properties_to_skip)

        description_key = f"secret_santa_participant_{participant.type.name}_description_prompt"
        await participant.editor_for(ctx, "description", prompt = ctx.translate(description_key))

        participant.save()
        await ctx.success("Your secret santa profile has been setup.")

    @secret_santa.command(name = "dropout")
    @commands.dm_only()
    async def secret_santa_dropout(self, ctx):
        """Dropout from participating in the secret santa event this year."""
        secret_santa = await SecretSantaHelper.get_secret_santa(ctx)
        participant  = SecretSantaRepository.get_participant(secret_santa_id = secret_santa.id, user_id = ctx.author.id)
        if participant is None:
            raise SendableException("You weren't participating yet.")
        if participant.giftee is not None or secret_santa.started_at is not None:
            raise SendableException("Unable to drop out at this stage (already started)")

        participant.delete()
        await ctx.success("You successfully dropped out of the secret santa event.")

    @tasks.loop(minutes = 1)
    async def poller(self):
        if self._secret_santa_in_progress:
            return

        self._secret_santa_in_progress = True
        for secret_santa in SecretSantaRepository.get_queue():
            try:
                participants = SecretSantaHelper.get_filtered_participants(secret_santa)
            except Exception as e:
                self.bot.log(e)
                continue

            secret_santa.started_at = datetime.datetime.utcnow()
            secret_santa.save()

            for type in participants:
                available_participants = [x for x in participants[type]]

                for participant in participants[type]:
                    giftee = SecretSantaHelper.get_random_giftee(available_participants, participant)
                    available_participants.remove(giftee)
                    embed  = SecretSantaUI.get_giftee_info_embed(giftee)
                    asyncio.gather(participant.user.send(embed = embed))
                    participant.giftee = giftee
                    participant.save()

        self._secret_santa_in_progress = False

def setup(bot):
    bot.add_cog(SecretSantaCog(bot))
