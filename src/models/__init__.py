from .base import BaseModel
from .human import Human, Item, HumanItem
from .intergalactica import Earthling, TemporaryChannel
from .analytics import EmojiUsage
from .settings import Settings, NamedEmbed, NamedChannel, Translation, Locale
from .ticket import Ticket, Reply
from .poll import Change, Parameter, Poll, PollTemplate, Vote, Option
from .scene import Scene, Scenario
from .pigeon import Pigeon, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date
from .admin import SavedEmoji, Location, DailyReminder
from .prank import NicknamePrank, Prankster
from .reddit import Subreddit

database = Human._meta.database

def setup():
    with database.connection_context():
        # database.drop_tables([Pigeon, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date ])
        database.create_tables([Pigeon, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date ])

        # database.drop_tables([SavedEmoji, Location, DailyReminder])
        database.create_tables([SavedEmoji, Location, DailyReminder])

        # database.drop_tables([Subreddit])
        database.create_tables([Subreddit])

        # database.drop_tables([NicknamePrank, Prankster])
        database.create_tables([NicknamePrank, Prankster])

        # database.drop_tables([Scene, Scenario])
        database.create_tables([Scene, Scenario])

        # database.drop_tables([Human, Item, HumanItem])
        database.create_tables([Human, Item, HumanItem])

        # database.drop_tables([Earthling, TemporaryChannel])
        database.create_tables([Earthling, TemporaryChannel])

        # database.drop_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])
        database.create_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])

        # database.drop_tables([EmojiUsage])
        database.create_tables([EmojiUsage])

        # database.drop_tables([Ticket, Reply])
        database.create_tables([Ticket, Reply])

        # database.drop_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])
        database.create_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])

setup()