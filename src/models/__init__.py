from .base import BaseModel

from .human import Human, GlobalHuman
from .analytics import EmojiUsage
from .settings import Settings, NamedEmbed, NamedChannel, Translation, Locale
# from .poll import Poll, Vote, Option
from .staff_communication import Ticket, Reply
from .poll import Change, Parameter, Poll, PollTemplate, Vote, Option

database = Human._meta.database

with database:
    # database.drop_tables([Human, GlobalHuman])
    database.create_tables([Human, GlobalHuman])

    # database.drop_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])
    database.create_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])

    # database.drop_tables([EmojiUsage])
    database.create_tables([EmojiUsage])

    # database.drop_tables([Ticket, Reply])
    database.create_tables([Ticket, Reply])

    # database.drop_tables   ([Change, Parameter, Poll, PollTemplate, Option, Vote])
    database.create_tables ([Change, Parameter, Poll, PollTemplate, Option, Vote])


