from . import BaseModel
from .base import MessageIdField, GuildIdField
from .helpers import create


@create()
class StarboardMapping(BaseModel):
    guild_id = GuildIdField()
    user_message_id = MessageIdField()
    bot_message_id = MessageIdField()

    class Meta:
        indexes = (
            (('user_message_id', 'bot_message_id'), True),
        )
