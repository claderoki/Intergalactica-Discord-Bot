from typing import Generator, Tuple
import random

import discord

from src.config import config
from src.models.pet import Pet, Mob


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


@config.tree.command(name="petfight", description="Have your pet fight something")
async def pet_fight(interaction: discord.Interaction):
    pet, _ = Pet.get_or_create(name='Hmm', guild_id=interaction.guild.id)
    fight = Fight(pet)
    pet_won = fight.start()
    log = '\n'.join(fight._log)
    if pet_won:
        log += f'\n{pet.name} won! You win 2 points to spend on upgrades.}'
    await interaction.response.send_message(f'```\n{log}```')
