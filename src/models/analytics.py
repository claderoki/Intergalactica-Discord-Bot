import peewee

from .base import BaseModel

class EmojiUsage(BaseModel):
    guild_id    = peewee.BigIntegerField  (null = False)
    emoji_id    = peewee.BigIntegerField  (null = False)
    total_uses  = peewee.IntegerField     (default = 0)

    @property
    def emoji(self):
        return self.bot.get_emoji(self.emoji_id)
