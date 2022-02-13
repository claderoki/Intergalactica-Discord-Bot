import io
from typing import Union

import discord

import src.config as config


class FileHelper:
    user_id = 771781840012705792

    @classmethod
    async def store(cls, file: Union[str, io.BytesIO], filename: str = None) -> str:
        """Stores a file in the designated storage channel and returns the URL of the newly stored image."""

        storage_channel = config.bot.get_user(cls.user_id)
        filename = filename or "file"

        if isinstance(file, io.BytesIO):
            file.seek(0)

        file = discord.File(fp=file, filename=filename)

        message = await storage_channel.send(file=file)
        return message.attachments[0].url
