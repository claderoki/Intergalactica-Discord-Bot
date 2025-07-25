import peewee

from .base import BaseModel
from .human import Human, Item, HumanItem, ItemCategory
from .intergalactica import Earthling, Reminder
from .settings import Translation, Locale, UserSetting
from .pigeon import Pigeon, PigeonRelationship, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date
from .prank import NicknamePrank, Prankster, EmojiPrank, RolePrank
from .reddit import Subreddit
from .intergalactica import Advertisement, AdvertisementSubreddit
from .conversation import Conversant, Conversation, Participant
from .conversions import Currency, Measurement, StoredUnit
from .crossroad import StarboardMapping
from .helpers import tables_to_create, tables_to_drop
from .game import GameStat
from .pet import Pet
from .calamity import Calamity

database: peewee.Database = BaseModel._meta.database
with database.connection_context():
    database.drop_tables(tables_to_drop)
    database.create_tables(tables_to_create)
