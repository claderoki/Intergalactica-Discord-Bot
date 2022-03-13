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

database = BaseModel._meta.database


def setup():
    with database.connection_context():
        # database.drop_tables([Milkyway, MilkywaySettings])
        database.create_tables([Milkyway, MilkywaySettings])

        # database.drop_tables([GuildRewardsProfile, GuildRewardsSettings])
        database.create_tables([GuildRewardsProfile, GuildRewardsSettings])

        # database.drop_tables([InactiveChannelsSettings])
        database.create_tables([InactiveChannelsSettings])

        # database.drop_tables([Conversant, Participant, Conversation])
        database.create_tables([Conversant, Participant, Conversation])

        # database.drop_tables([Advertisement, AdvertisementSubreddit])
        database.create_tables([Advertisement, AdvertisementSubreddit])

        # database.drop_tables([Currency, Measurement])
        database.create_tables([Currency, Measurement])

        # database.drop_tables([MentionGroup, MentionMember])
        database.create_tables([MentionGroup, MentionMember])

        # database.drop_tables([Pigeon, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, PigeonRelationship, Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile])
        database.create_tables(
            [Pigeon, PigeonRelationship, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date])

        # database.drop_tables([SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word, DailyActivity, GameRole, GameRoleSettings])
        database.create_tables([Giveaway, DailyActivity, GameRole,GameRoleSettings])

        # database.drop_tables([Subreddit])
        database.create_tables([Subreddit])

        # database.drop_tables([NicknamePrank, Prankster, EmojiPrank, RolePrank])
        database.create_tables([NicknamePrank, Prankster, EmojiPrank, RolePrank])

        # database.drop_tables([Scene, Scenario])
        database.create_tables([Scene, Scenario])

        # database.drop_tables([Human, Item, HumanItem, ItemCategory])
        database.create_tables([Human, Item, HumanItem, ItemCategory])

        # database.drop_tables([Earthling, TemporaryChannel, Reminder, TemporaryVoiceChannel, TemporaryTextChannel])
        database.create_tables([Earthling, TemporaryChannel, Reminder, TemporaryVoiceChannel, TemporaryTextChannel])

        # database.drop_tables([UserSetting, Locale, Translation])
        database.create_tables([UserSetting, Locale, Translation])

        # database.drop_tables([Ticket, Reply])
        database.create_tables([Ticket, Reply])

        # database.drop_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])
        database.create_tables([Poll, PollTemplate, Option, Vote])

setup()
