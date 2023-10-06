import discord
import src.config as config


@config.tree.command(
    name="tteeeee",
    description="My first application Command",
    guild=discord.Object(id=1158799313275719780)
)
async def first_command(interaction):
    await interaction.response.send_message("Hello!")
