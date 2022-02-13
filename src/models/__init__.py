from .admin import SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word, DailyActivity, GameRole, \
    GameRoleSettings
from .base import BaseModel
from .conversation import Conversant, Conversation, Participant
from .conversions import Currency, Measurement, StoredUnit
from .farming import Farm, Crop, FarmCrop
from .guildrewards import GuildRewardsProfile, GuildRewardsSettings
from .human import Human, Item, HumanItem, ItemCategory
from .inactivechannels import InactiveChannelsSettings
from .intergalactica import Advertisement, AdvertisementSubreddit
from .intergalactica import Earthling, Reminder, TemporaryVoiceChannel, TemporaryTextChannel, TemporaryChannel
from .intergalactica import MentionGroup, MentionMember
from .milkyway import Milkyway, MilkywaySettings
from .pigeon import Pigeon, PigeonRelationship, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, \
    Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile
from .poll import Change, Parameter, Poll, PollTemplate, Vote, Option
from .prank import NicknamePrank, Prankster, EmojiPrank, RolePrank
from .qotd import Category, Question, CategoryChannel, QuestionConfig
from .reddit import Subreddit
from .scene import Scene, Scenario
from .secretsanta import SecretSanta, SecretSantaParticipant
from .settings import Settings, NamedChannel, Translation, Locale, UserSetting
from .ticket import Ticket, Reply

database = BaseModel._meta.database


def setup():
    with database.connection_context():
        # database.drop_tables([GuildRewardsProfile, GuildRewardsSettings])
        database.create_tables([GuildRewardsProfile, GuildRewardsSettings])

        # database.drop_tables([InactiveChannelsSettings])
        database.create_tables([InactiveChannelsSettings])

        # database.drop_tables([Conversant, Participant, Conversation])
        database.create_tables([Conversant, Participant, Conversation])

        # database.drop_tables([SecretSanta, SecretSantaParticipant])
        database.create_tables([SecretSanta, SecretSantaParticipant])

        # database.drop_tables([Advertisement, AdvertisementSubreddit])
        database.create_tables([Advertisement, AdvertisementSubreddit])

        # database.drop_tables([Currency, Measurement])
        database.create_tables([Currency, Measurement])

        # database.drop_tables([Farm, Crop, FarmCrop])
        database.create_tables([Farm, Crop, FarmCrop])

        # database.drop_tables([MentionGroup, MentionMember])
        database.create_tables([MentionGroup, MentionMember])

        # database.drop_tables([Category, Question, CategoryChannel, QuestionConfig])
        database.create_tables([Category, Question, CategoryChannel, QuestionConfig])

        # database.drop_tables([Pigeon, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, PigeonRelationship, Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile])
        database.create_tables(
            [Pigeon, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, PigeonRelationship, Buff,
             PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile])

        # database.drop_tables([SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word, DailyActivity, GameRole, GameRoleSettings])
        database.create_tables(
            [SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word, DailyActivity, GameRole,
             GameRoleSettings])

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

        # database.drop_tables([Settings, UserSetting, NamedChannel, Locale, Translation])
        database.create_tables([Settings, UserSetting, NamedChannel, Locale, Translation])

        # database.drop_tables([Ticket, Reply])
        database.create_tables([Ticket, Reply])

        # database.drop_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])
        database.create_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])


setup()
