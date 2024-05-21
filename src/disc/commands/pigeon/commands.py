import datetime
import random
from typing import Callable, List, Union

import discord
from discord.app_commands import guild_only
from discord.ext import commands
from discord import app_commands

from src.disc.commands.base.cog import BaseGroupCog
from src.disc.commands.base.decorators import extras
from src.disc.commands.base.probabilities import Probabilities, Probability
from src.disc.commands.base.validation import has_gold
from src.utils.enums import Gender
from .validation import *
from src.disc.commands.pigeon.helpers import PigeonHelper
from src.disc.commands.pigeon.ui import SpaceActionView
from src.disc.helpers.pretty import prettify_dict
from src.models import Pigeon
from src.models.pigeon import ExplorationPlanetLocation, SpaceExploration, PigeonRelationship, Gendered
from src.utils.stats import Winnings, HumanStat, PigeonStat


class CustomPlaceholder:
    def __init__(self, placeholder: str, getter: Union[Callable[[], str], str]):
        self.placeholder = placeholder
        self._value = getter

    def get_value(self):
        if callable(self._value):
            return self._value()
        return self._value


def pigeon_placeholders(pigeon: Pigeon, pigeon2: Optional[Pigeon] = None) -> List[CustomPlaceholder]:
    return [
        CustomPlaceholder('[his]', pigeon.gender.get_posessive_pronoun()),
        CustomPlaceholder('[him]', pigeon.gender.get_pronoun()),
        CustomPlaceholder('[her]', pigeon2.gender.get_posessive_pronoun()),
        CustomPlaceholder('[she]', pigeon2.gender.get_pronoun()),
        CustomPlaceholder('[jonas]', pigeon.name),
        CustomPlaceholder('[martha]', pigeon2.name),
    ]


class MessageBuilder:
    def __init__(self, initial: str = None):
        self.lines = []
        if initial:
            self.lines.append(initial)

    def add_line(self, line: str = None):
        if line:
            self.lines.append(line)

    def format(self, custom_placeholders: List[CustomPlaceholder] = None) -> str:
        lines = '\n'.join(self.lines)
        if custom_placeholders:
            for placeholder in custom_placeholders:
                lines = lines.replace(placeholder.placeholder, placeholder.get_value())
        return lines


class StatUpdate(Probability):
    __slots__ = ('probability', 'gain', 'cost', 'message')

    def __init__(self, gain: int, cost: int, message: str, probability: float):
        super().__init__(probability)
        self.gain = gain
        self.cost = cost
        self.message = message


def probabilities(*updates: StatUpdate):
    return extras('probabilities', Probabilities(list(updates)))


class Pigeon2(BaseGroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.helper = PigeonHelper()

    async def __update_stat(self, interaction: discord.Interaction, stat: PigeonStat, cost: int, message: str):
        targets = await self.validate(interaction)
        winnings = Winnings(stat, HumanStat.gold(-cost))
        targets.get_pigeon().update_winnings(winnings)
        await interaction.response.send_message(message + '\n' + winnings.format())

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
        StatUpdate(20, 20, 'You give your pigeon a regular bath.', 1),
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

    @has_pigeon()
    @has_status(Pigeon.Status.idle)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="explore", description="Send your pigeon to space")
    async def explore(self, interaction: discord.Interaction):
        targets = await self.validate(interaction)
        pigeon = targets.get_pigeon()

        location: ExplorationPlanetLocation = random.choice(list(self.helper.get_all_locations()))
        id = location.id
        image_url = location.image_url or location.planet.image_url
        arrival_date = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

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
        await interaction.response.send_message('OK, your pigeon is on its way.')

    @has_pigeon()
    @has_status(Pigeon.Status.space_exploring)
    @commands.max_concurrency(1, commands.BucketType.user)
    @app_commands.command(name="space", description="Get your pigeon back from space")
    async def space(self, interaction: discord.Interaction):
        targets = await self.validate(interaction)
        exploration: SpaceExploration = SpaceExploration.get_or_none(pigeon=targets.get_pigeon(), finished=False)
        if exploration is None:
            targets.get_pigeon().status = Pigeon.Status.idle
            targets.get_pigeon().save()
            await interaction.response.send_message('Weird')
            return

        if exploration.arrival_date > datetime.datetime.utcnow():
            await interaction.response.send_message('Your pigeon is still on its way.')
            return

        location = self.helper.find_location(exploration.location.id)

        menu = SpaceActionView(interaction.user, list(location.actions), exploration)
        desc = [f'You arrive at {location.planet.name} ({location.name}).', 'What action would you like to perform?']
        embed = discord.Embed(description='\n\n'.join(desc))
        await interaction.response.send_message(embed=embed, view=menu)
        r = await interaction.original_response()
        menu.refresh = lambda: r.edit(embed=embed, view=menu)
        await menu.wait()

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
        message.add_line('Your pigeon successfully poops on [martha] and to finish it off, [jonas] '
                         'wipes [his] butt clean on [her] fur.')
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

    # @has_pigeon()
    # @app_commands.command(name="test", description="test")
    # async def test(self, interaction: discord.Interaction):
    #     targets = await self.validate(interaction)
    #
    #     winnings = Winnings(HumanStat.gold(10), HumanStat.item(Item.get(id=82)))
    #
    #     embed = discord.Embed()
    #     embed.title = 'Title'
    #     embed.description = winnings.format()
    #     await interaction.response.send_message(embed=embed)

    # @app_commands.command(name="manage", description="Manage")
    # async def manage(self, interaction: discord.Interaction):
    #     process_scenarios()
    # model = ExplorationActionScenario()
    # model.action = 2
    # await edit_view(interaction, model, forms_to_view(model, guess_for_fields([ExplorationActionScenario.text])))
    # model.save()
    # await interaction.followup.send(content='Saved')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pigeon2(bot))
