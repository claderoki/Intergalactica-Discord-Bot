
from discord.ext import commands
from discord import app_commands

from src.disc.commands.base.cog import BaseGroupCog
from src.disc.commands.base.validation import does_not_have_pigeon, has_status, has_gold, has_pigeon
from src.disc.commands.pigeon.helpers import PigeonHelper
from src.disc.commands.base.view import *
from src.disc.commands.pigeon.ui import SpaceActionView
from src.models.pigeon import *
from src.resources import process_scenarios


class Pigeon2(BaseGroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.helper = PigeonHelper()

    async def __update_stat(self, interaction: discord.Interaction, stat: PigeonStat, cost: int, message: str):
        result = self.check(user_id=interaction.user.id)
        if result.errors:
            await interaction.response.send_message(result.errors[0])
            return

        winnings = Winnings(stat, HumanStat.gold(-cost))
        result.pigeon.update_winnings(winnings)
        await interaction.response.send_message(message + '\n' + winnings.format())

    @has_pigeon()
    @app_commands.command(name="feed", description="Feed your pigeon.")
    async def feed(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.food(20), 20, 'You feed that thing you call a pigeon.')

    @has_pigeon()
    @app_commands.command(name="clean", description="Clean your pigeon.")
    async def clean(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.cleanliness(20), 20, 'You clean that thing you call a pigeon.')

    @has_pigeon()
    @app_commands.command(name="play", description="Play with your pigeon.")
    async def play(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.happiness(20), 20,
                                 'You play with that thing you call a pigeon.')

    @has_pigeon()
    @app_commands.command(name="heal", description="Heal your pigeon.")
    async def heal(self, interaction: discord.Interaction) -> None:
        await self.__update_stat(interaction, PigeonStat.health(20), 20, 'You heal that thing you call a pigeon.')

    @does_not_have_pigeon()
    @has_gold(250)
    @app_commands.command(name="buy", description="Buy a pigeon.")
    async def buy(self, interaction: discord.Interaction, name: str):
        targets = await self.validate(interaction)
        pigeon = Pigeon.create(name=name, human=targets.get_human())
        winnings = Winnings(HumanStat.gold(-250))
        pigeon.update_winnings(winnings)
        await interaction.response.send_message('Sure\n' + winnings.format())

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
        arrival_date = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)

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
        exploration: SpaceExploration = SpaceExploration.get(pigeon=targets.get_pigeon(), finished=False)

        if exploration.arrival_date > datetime.datetime.utcnow():
            await interaction.response.send_message('Still traveling, dumbass')
            return

        location = self.helper.find_location(exploration.location.id)

        menu = SpaceActionView(interaction.user, list(location.actions), exploration)
        desc = [f'You arrive at {location.planet.name} ({location.name}).', 'What action would you like to perform?']
        embed = discord.Embed(description='\n\n'.join(desc))
        await interaction.response.send_message(embed=embed, view=menu)
        r = await interaction.original_response()
        menu.refresh = lambda: r.edit(embed=embed, view=menu)
        await menu.wait()

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
