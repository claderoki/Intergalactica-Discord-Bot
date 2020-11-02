from .base import BaseModel
from .human import Human
from .intergalactica import Earthling
from .analytics import EmojiUsage
from .settings import Settings, NamedEmbed, NamedChannel, Translation, Locale
from .staff_communication import Ticket, Reply
from .poll import Change, Parameter, Poll, PollTemplate, Vote, Option
# from .assassins import Game, Player, KillMessage
from .scene import Scene, Scenario
from .pigeon import Pigeon, Fight, Exploration, Mail
from .admin import SavedEmoji
from .prank import NicknamePrank, Prankster

database = Human._meta.database

def setup():
    with database:
        # database.drop_tables([Pigeon, Fight, Exploration, Mail])
        database.create_tables([Pigeon, Fight, Exploration, Mail ])

        # database.drop_tables([SavedEmoji])
        database.create_tables([SavedEmoji])

        database.drop_tables([NicknamePrank, Prankster])
        database.create_tables([NicknamePrank, Prankster])

        # database.drop_tables([Scene, Scenario])
        database.create_tables([Scene, Scenario])

        # database.drop_tables([Human])
        database.create_tables([Human])

        # database.drop_tables([Earthling])
        database.create_tables([Earthling])

        # database.drop_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])
        database.create_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])

        # database.drop_tables([EmojiUsage])
        database.create_tables([EmojiUsage])

        # database.drop_tables([Ticket, Reply])
        database.create_tables([Ticket, Reply])

        # database.drop_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])
        database.create_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])

        # database.drop_tables([Game, Player, KillMessage])
        # database.create_tables([Game, Player, KillMessage])

setup()