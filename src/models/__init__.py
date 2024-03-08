import peewee

from .base import BaseModel
from .human import Human, Item, HumanItem, ItemCategory
from .intergalactica import Earthling, Reminder, TemporaryVoiceChannel, TemporaryTextChannel, TemporaryChannel
from .settings import Translation, Locale, UserSetting
from .ticket import Ticket, Reply
from .poll import Poll, PollTemplate, Vote, Option
from .scene import Scene, Scenario
from .pigeon import Pigeon, PigeonRelationship, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date
from .admin import Giveaway, DailyActivity, GameRole, GameRoleSettings
from .prank import NicknamePrank, Prankster, EmojiPrank, RolePrank
from .reddit import Subreddit
from .intergalactica import MentionGroup, MentionMember
from .intergalactica import Advertisement, AdvertisementSubreddit
from .conversation import Conversant, Conversation, Participant
from .conversions import Currency, Measurement, StoredUnit
from .inactivechannels import InactiveChannelsSettings
from .milkyway import Milkyway, MilkywaySettings
from .guildrewards import GuildRewardsProfile, GuildRewardsSettings
from .helpers import tables_to_create, tables_to_drop
from .game import GameStat

database: peewee.Database = BaseModel._meta.database
with database.connection_context():
    database.drop_tables(tables_to_drop)
    database.create_tables(tables_to_create)
