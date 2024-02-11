from enum import Enum

import discord
from discord import app_commands

from src.config import config
from src.wrappers.hue_bridge import UpdateLightCall, GetLightCall


class Lights(Enum):
    MAIN = 1
    CORNER = 2


@config.tree.command(name="togglelight",
                     guild=discord.Object(id=1163169122868269187))
async def togglelight(interaction: discord.Interaction, light: Lights, brightness: app_commands.Range[int, 0, 250]):
    username = config.environ.get('hue_bridge_username')
    current_light = GetLightCall(username, light.value).call()
    state = current_light.state
    previous_brightness = state.brightness
    if brightness == 0:
        state.on = False
    state.brightness = brightness
    UpdateLightCall(username, light.value, state).call()

    await interaction.response.send_message(f'Changed light {light.name} brightness from {brightness} to  {previous_brightness}')
