from .base import BaseModel

from .human import Human, GlobalHuman
from .analytics import EmojiUsage
from .settings import Settings, NamedEmbed, NamedChannel, Translation, Locale
from .poll import Poll, Vote, Option
from .staff_communication import Ticket, Reply


database = Human._meta.database

with database:
    database.create_tables([Human, GlobalHuman])

    # database.drop_tables([Settings, NamedChannel, Locale, Translation])
    database.create_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])

    database.create_tables([EmojiUsage])
    database.create_tables([Ticket, Reply])
    database.create_tables([Poll, Option, Vote])


