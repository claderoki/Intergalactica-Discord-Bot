import datetime
import enum
import random
import re
from typing import Callable, List, Union, Any

import discord
from discord.app_commands import guild_only
from discord.ext import commands
from discord import app_commands, Colour
from discord.types.embed import EmbedType

from src.disc.commands.base.cog import BaseGroupCog
from src.disc.commands.base.decorators import extras
from src.disc.commands.base.probabilities import Probabilities, Probability
from src.disc.commands.base.validation import has_gold
from src.utils.country import Country
from .validation import *
from src.disc.commands.pigeon.helpers import PigeonHelper
from src.disc.commands.pigeon.ui import SpaceActionView
from src.disc.helpers.pretty import prettify_dict
from src.models import Pigeon, Reminder
from src.models.pigeon import ExplorationPlanetLocation, SpaceExploration, PigeonRelationship, Gendered, Exploration
from src.utils.stats import Winnings, HumanStat, PigeonStat
from ..base.view import ReminderMenu
from ...cogs.pigeon.exploration_retrieval import ExplorationRetrieval, MailRetrieval


class CustomPlaceholder:
    def __init__(self, placeholder: str, getter: Union[Callable[[], str], str]):
        self.placeholder = placeholder
        self._value = getter

    def _get_value(self):
        if callable(self._value):
            return self._value()
        return self._value

    def get_value(self, placeholder: str) -> str:
        value = self._get_value()
        # Adjust capitalization based on the placeholder pattern
        if placeholder.isupper():
            return value.upper()
        elif placeholder[1].isupper():
            return value.capitalize()
        return value


def pigeon_placeholders(pigeon: 'Pigeon', pigeon2: Optional['Pigeon'] = None) -> List[CustomPlaceholder]:
    pronouns = pigeon.get_pronouns()
    placeholders = [
        CustomPlaceholder('[name]', pigeon.name),
        CustomPlaceholder('[they]', pronouns.subject),
        CustomPlaceholder('[them]', pronouns.object),
        CustomPlaceholder('[their]', pronouns.possessive_adjective),
        CustomPlaceholder('[theirs]', pronouns.possessive_pronoun),
        CustomPlaceholder('[themselves]', pronouns.reflexive),
    ]

    if pigeon2:
        pronouns = pigeon2.get_pronouns()
        placeholders.extend([
            CustomPlaceholder('[name2]', pigeon2.name),
            CustomPlaceholder('[they2]', pronouns.subject),
            CustomPlaceholder('[them2]', pronouns.object),
            CustomPlaceholder('[their2]', pronouns.possessive_adjective),
            CustomPlaceholder('[theirs2]', pronouns.possessive_pronoun),
            CustomPlaceholder('[themselves2]', pronouns.reflexive),
        ])

    return placeholders


def format_placeholders(placeholders: List[CustomPlaceholder], text: str):
    if not placeholders:
        return text
    for placeholder in placeholders:
        pattern = re.compile(re.escape(placeholder.placeholder), re.IGNORECASE)
        matches = pattern.findall(text)
        for match in matches:
            text = text.replace(match, placeholder.get_value(match), 1)
    return text


class MessageBuilder:
    def __init__(self, initial: str = None):
        self.lines = []
        if initial:
            self.lines.append(initial)

    def add_line(self, line: str = None):
        if line:
            self.lines.append(line)

    def format(self, custom_placeholders: List[CustomPlaceholder] = None) -> str:
        return format_placeholders(custom_placeholders, '\n'.join(self.lines))


class C3POEmbed(discord.Embed):
    def __init__(self, *, colour: Optional[Union[int, Colour]] = None, color: Optional[Union[int, Colour]] = None,
                 title: Optional[Any] = None, type: EmbedType = 'rich', url: Optional[Any] = None,
                 description: Optional[Any] = None, timestamp: Optional[datetime.datetime] = None,
                 placeholders: List[CustomPlaceholder] = None):
        self._placeholders = placeholders
        super().__init__(colour=colour, color=color or discord.Color.from_rgb(242, 180, 37), title=title, type=type, url=url,
                         description=self._format_placeholders(description),
                         timestamp=timestamp)

    def _format_placeholders(self, text: str) -> str:
        return format_placeholders(self._placeholders, text)


class StatUpdate(Probability):
    __slots__ = ('probability', 'gain', 'cost', 'message')

    def __init__(self, gain: int, cost: int, message: str, probability: float):
        super().__init__(probability)
        self.gain = gain
        self.cost = cost
        self.message = message


def probabilities(*updates: StatUpdate):
    return extras('probabilities', Probabilities(list(updates)))


def quick_message(message: str, pigeon: Pigeon):
    return MessageBuilder(message).format(pigeon_placeholders(pigeon))


class Pigeon2(BaseGroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.helper = PigeonHelper()

    async def __update_stat(self, interaction: discord.Interaction, stat: PigeonStat, cost: int, message: str):
        targets = await self.validate(interaction)
        winnings = Winnings(stat, HumanStat.gold(-cost))
        targets.get_pigeon().update_winnings(winnings)
        await interaction.response.send_message(quick_message(message, targets.get_pigeon()) + '\n' + winnings.format())

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @food_less_than(100, 'Your pigeon is already full.')
    @probabilities(
        StatUpdate(20, 20, 'You feed your pigeon some regular seeds.', 1),
        StatUpdate(25, 20, 'You feed your pigeon some premium seeds.', 0.1),
        StatUpdate(100, 10, 'Your pigeon gets a great deal on some very rejuvenating fries.', 0.01),
    )
    @app_commands.command(name="feed", description="Feed your pigeon.")
    async def feed(self, interaction: discord.Interaction):
        outcome: StatUpdate = self.probability(interaction)
        await self.__update_stat(interaction, PigeonStat.food(outcome.gain), outcome.cost, outcome.message)

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @cleanliness_less_than(100, 'Your pigeon is already clean.')
    @probabilities(
        StatUpdate(20, 20, 'You give [name] a good wash. '
                           '[They] rubs [their] head on your hand as a sign of gratitude', 1),
        StatUpdate(25, 20, 'You give your pigeon a premium bath.', 0.1),
        StatUpdate(100, 10, 'Your pigeon gets a great deal on some very good soap.', 0.01),
    )
    @app_commands.command(name="clean", description="Clean your pigeon.")
    async def clean(self, interaction: discord.Interaction):
        outcome: StatUpdate = self.probability(interaction)
        await self.__update_stat(interaction, PigeonStat.cleanliness(outcome.gain), outcome.cost, outcome.message)

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @happiness_less_than(100, 'Your pigeon is already really happy.')
    @app_commands.command(name="play", description="Play with your pigeon.")
    async def play(self, interaction: discord.Interaction):
        await self.__update_stat(interaction, PigeonStat.happiness(20), 20,
                                 'You play fetch with your pigeon.')

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @health_less_than(100, 'Your pigeon is already very healthy.')
    @app_commands.command(name="heal", description="Heal your pigeon.")
    async def heal(self, interaction: discord.Interaction):
        await self.__update_stat(interaction, PigeonStat.health(20), 20, 'You heal your pigeon!')

    @does_not_have_pigeon()
    @has_gold(50)
    @app_commands.command(name="buy", description="Buy a pigeon.")
    async def buy(self, interaction: discord.Interaction, name: str):
        targets = await self.validate(interaction)
        pigeon = Pigeon.create(name=name, human=targets.get_human())
        winnings = Winnings(HumanStat.gold(-50))
        pigeon.update_winnings(winnings)
        await interaction.response.send_message('All right, I\'ve given you a pigeon.\n' + winnings.format())

    @has_pigeon()
    @app_commands.command(name="profile", description="Check the status of your pigeon.")
    async def profile(self, interaction: discord.Interaction):
        targets = await self.validate(interaction)
        pigeon = targets.get_pigeon()

        data = {}
        emojis = []

        for stat in pigeon.get_stats():
            data[stat.name] = str(stat.amount)
            emojis.append(stat.emoji)

        emojis.append(pigeon.status.value)
        data['status'] = pigeon.status.name
        lines = prettify_dict(data, emojis=emojis)
        embed = discord.Embed(description=f'```\n{lines}```')
        await interaction.response.send_message(embed=embed)

    async def space_explore(self, interaction: discord.Interaction, pigeon: Pigeon):
        location: ExplorationPlanetLocation = random.choice(list(self.helper.get_all_locations()))
        image_url = location.image_url or location.planet.image_url
        arrival_date = datetime.datetime.utcnow() + datetime.timedelta(minutes=random.randint(60, 120))

        SpaceExploration.create(
            location=id,
            start_date=datetime.datetime.utcnow(),
            arrival_date=arrival_date,
            end_date=None,
            pigeon=pigeon,
            actions_remaining=3,
            total_actions=3
        )

        pigeon.status = Pigeon.Status.space_exploring
        pigeon.save()
        embed = C3POEmbed(description=f'Okay. Your pigeon is on [their] way to '
                                      f'{location.name} ({location.planet.name}).',
                          placeholders=pigeon_placeholders(pigeon))
        embed.set_thumbnail(url=image_url)
        menu = ReminderMenu(arrival_date, 'Your pigeon is back')
        await interaction.response.send_message(embed=embed, view=menu)

    async def earth_explore(self, interaction, pigeon):
        human = pigeon.human

        residence = human.country or Country.random()
        destination = Country.random()

        exploration = Exploration(residence=residence, destination=destination, pigeon=pigeon)
        exploration.end_date = exploration.start_date + datetime.timedelta(minutes=exploration.calculate_duration())
        pigeon.status = Pigeon.Status.exploring
        pigeon.save()
        exploration.save()

        embed = C3POEmbed()
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png"
        )
        embed.description = 'Okay. Your pigeon is now off to explore a random location!'
        menu = ReminderMenu(exploration.end_date, 'Your pigeon is back')
        await interaction.response.send_message(embed=embed, view=menu)

    class ExplorationType(enum.Enum):
        space = 1
        earth = 2

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="explore", description="Send your pigeon to space")
    async def explore(self, interaction: discord.Interaction, type: ExplorationType):
        targets = await self.validate(interaction)
        pigeon = targets.get_pigeon()
        if type == self.ExplorationType.space:
            await self.space_explore(interaction, pigeon)
        elif type == self.ExplorationType.earth:
            await self.earth_explore(interaction, pigeon)

    @has_pigeon()
    @status_in(Pigeon.Status.space_exploring, Pigeon.Status.exploring, Pigeon.Status.mailing)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="retrieve", description="Retrieve your pigeon from its current activity")
    async def retrieve(self, interaction: discord.Interaction):
        targets = await self.validate(interaction)
        pigeon = targets.get_pigeon()
        if pigeon.status == Pigeon.Status.space_exploring:
            await self.retrieve_from_space(interaction, pigeon)
        elif pigeon.status == Pigeon.Status.exploring:
            await self.retrieve_from_earth(interaction, pigeon)
        elif pigeon.status == Pigeon.Status.mailing:
            await self.retrieve_from_mail(interaction, pigeon)

    async def retrieve_from_mail(self, interaction, pigeon):
        activity = pigeon.current_activity
        if activity.end_date_passed:
            retrieval = MailRetrieval(activity)
            embed = retrieval.embed
            retrieval.commit()

            Reminder.create(
                user_id=activity.recipient.user_id,
                channel_id=None,
                message=self.bot.translate("pigeon_inbox_unread_mail"),
                due_date=datetime.datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = C3POEmbed()
            embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to send a message!"
            embed.set_footer(text="Check back at",
                             icon_url="https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
            embed.timestamp = activity.end_date.replace(tzinfo=datetime.timezone.utc)
            await interaction.response.send_message(embed=embed)

    async def retrieve_from_earth(self, interaction, pigeon):
        activity = pigeon.current_activity
        if isinstance(activity, Exploration):
            if activity.end_date_passed:
                retrieval = ExplorationRetrieval(activity)
                embed = retrieval.embed
                retrieval.commit()
                await interaction.response.send_message(embed=embed)
            else:
                embed = C3POEmbed()
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to explore!"
                embed.set_footer(text="Check back at",
                                 icon_url="https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date.replace(tzinfo=datetime.timezone.utc)
                await interaction.response.send_message(embed=embed)

    async def retrieve_from_space(self, interaction, pigeon):
        exploration: SpaceExploration = SpaceExploration.get_or_none(pigeon=pigeon, finished=False)
        if exploration is None:
            pigeon.status = Pigeon.Status.idle
            pigeon.save()
            await interaction.response.send_message('Weird')
            return

        if exploration.arrival_date > datetime.datetime.utcnow():
            await interaction.response.send_message(quick_message('Your pigeon is still on [their] way.', pigeon))
            return

        location = self.helper.find_location(exploration.location.id)

        menu = SpaceActionView(interaction.user, list(location.actions), exploration)
        desc = [f'Your pigeon arrives at {location.planet.name} ({location.name}).',
                quick_message('What action would you like for [them] to perform?', pigeon)
                ]

        embed = discord.Embed(description='\n\n'.join(desc))
        await interaction.response.send_message(embed=embed, view=menu)
        r = await interaction.original_response()
        menu.refresh = lambda: r.edit(embed=embed, view=menu)
        await menu.wait()

    @has_pigeon()
    @has_status(Pigeon.Status.space_exploring)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="space", description="Get your pigeon back from space")
    async def space(self, interaction: discord.Interaction):
        targets = await self.validate(interaction)
        pigeon = targets.get_pigeon()
        await self.retrieve_from_space(interaction, pigeon)

    @has_pigeon()
    @guild_only()
    @has_status(Pigeon.Status.idle)
    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="poop", description="Poop on another pigeon.")
    async def poop(self, interaction: discord.Interaction, member: discord.Member):
        targets = await self.validate(interaction)
        other_targets = await self.validate(interaction, user_id=member.id, other=True)
        pigeon = targets.get_pigeon()
        pigeon2 = other_targets.get_pigeon()

        price = 5
        relationship = PigeonRelationship.get_or_create_for(pigeon, pigeon2)
        relationship.score -= price
        relationship.save()

        embed = discord.Embed()
        message = MessageBuilder()
        message.add_line('Your pigeon successfully poops on [name2] and to finish it off, [name] '
                         'wipes [their] butt clean on [their2] fur.')
        message.add_line()

        message.add_line(pigeon.name)
        winnings = Winnings(PigeonStat.cleanliness(5))
        message.add_line(winnings.format())
        pigeon.poop_victim_count += 1
        pigeon.update_winnings(winnings)

        message.add_line(pigeon2.name)
        winnings2 = Winnings(PigeonStat.cleanliness(-10))
        message.add_line(winnings2.format())
        pigeon2.pooped_on_count += 1
        pigeon2.update_winnings(winnings2)

        embed.description = message.format(pigeon_placeholders(pigeon, pigeon2))

        embed.set_footer(text=f"-{price} relations")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pigeon2(bot))
