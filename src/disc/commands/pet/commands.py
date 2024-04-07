import random
import typing

import discord
from discord import app_commands
from discord.ext import commands

from src.disc.commands.base.cog import BaseGroupCog
from src.models.pet import Pet, Mob, PetCaretaker, Vampiric, MushroomExpert, PetPerk, Perk
from src.utils.stats import Stat, Winnings


class PetCaretakerStat(Stat):
    @classmethod
    def trust(cls, amount: int) -> typing.Self:
        return cls('trust', amount, emoji='💩')

    @classmethod
    def points(cls, amount: int) -> typing.Self:
        return cls('points', amount, emoji='🌾')


class PerkButton(discord.ui.Button):
    def __init__(self, pet_perk: PetPerk):
        perk = pet_perk.perk
        super().__init__(
            label=f'{perk.name} {pet_perk.points}/{perk.cost}',
            emoji=perk.emoji
        )
        self.disabled = pet_perk.points >= perk.cost
        self.pet_perk = pet_perk


class PerkMenu(discord.ui.View):
    def __init__(self, pet: Pet, pet_perks: typing.List[PetPerk]):
        super(PerkMenu, self).__init__()
        self.pet = pet
        self.pet_perks = pet_perks

        for pet_perk in self.pet_perks:
            button = PerkButton(pet_perk)
            button.callback = self._create_callback_for(button)
            self.add_item(button)

    async def refresh(self):
        pass

    def _create_callback_for(self, button: PerkButton):
        def wrapper(interaction: discord.Interaction):
            return self._callback(button, interaction)
        return wrapper

    async def _callback(self, button: PerkButton, interaction: discord.Interaction):
        # todo, only allow for the person who started it to interact?

        caretaker, _ = PetCaretaker.get_or_create(user_id=interaction.user.id, pet=self.pet)
        if caretaker.points <= 0:
            print('ERROR', 'caretaker.points <= 0')
            # error
            return

        price = 1
        caretaker.points -= price
        button.pet_perk.points += price
        button.pet_perk.save()
        await interaction.response.defer()
        await self.refresh()


class Fight:
    def __init__(self, pet: Pet):
        self._log = []
        self._pet = pet
        self._mob = Mob('Slime', 100, (7, 13))

    def _gen(self):
        while True:
            yield self._pet, self._mob
            yield self._mob, self._pet

    def start(self) -> bool:
        for attacker, defender in self._gen():
            dmg = random.randint(*attacker.damage)
            defender.health -= dmg
            self._log.append(f'{attacker.name} deals {dmg} damage to {defender.name}')
            if defender.health <= 0:
                self._log.append(f'{attacker.name} wins')
                return attacker == self._pet


class PetCog(BaseGroupCog, name='pet'):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    def _get_pet(self, user_id: int, guild_id: int):
        pet, _ = Pet.get_or_create(name='Cherry', guild_id=guild_id)
        caretaker, _ = PetCaretaker.get_or_create(user_id=user_id, pet=pet)
        return pet, caretaker

    @app_commands.command(name='feed', description='Feed the server pet')
    async def feed(self, interaction: discord.Interaction):
        pet, caretaker = self._get_pet(interaction.user.id, interaction.guild.id)
        winnings = Winnings(PetCaretakerStat.trust(1), PetCaretakerStat.points(1))
        await interaction.response.send_message(f'You feed {pet.name}, {winnings.format()}')
        caretaker.update_winnings(winnings)
        caretaker.save()

    @app_commands.command(name='fight', description='Have your pet fight something')
    async def fight(self, interaction: discord.Interaction):
        pet, caretaker = self._get_pet(interaction.user.id, interaction.guild.id)
        fight = Fight(pet)
        pet_won = fight.start()
        log = '\n'.join(fight._log)
        winnings = Winnings()
        if pet_won:
            winnings.add_stat(PetCaretakerStat.points(2))
            log += f'\n{pet.name} won! {winnings.format()}'
            caretaker.update_winnings(winnings)
            caretaker.save()
        await interaction.response.send_message(f'```\n{log}```')

    @app_commands.command(name='perks', description='Manage the pets perks')
    async def perks(self, interaction: discord.Interaction):
        pet, caretaker = self._get_pet(interaction.user.id, interaction.guild.id)
        available_perks = [Vampiric, MushroomExpert]
        codes = [x.code for x in available_perks]
        query = PetPerk.select().where(PetPerk.code.in_(codes))
        missing = list(codes)

        perks: typing.List[PetPerk] = []
        for perk in query:
            perks.append(perk)
            missing.remove(perk.code)

        for perk in missing:
            perks.append(PetPerk(pet=pet, code=perk))

        menu = PerkMenu(pet, perks)
        await interaction.response.send_message(view=menu)
        response = await interaction.original_response()
        menu.refresh = lambda: response.edit(view=menu)
        await menu.wait()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PetCog(bot))
