import discord
from discord.ext import commands
from discord import app_commands


class Pigeon2(commands.GroupCog, name="pigeon"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="feed", description="Feed your pigeon.")
    async def feed(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from sub command 1")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pigeon2(bot))
