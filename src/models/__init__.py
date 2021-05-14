from .base import BaseModel
from .human import Human, Item, HumanItem, ItemCategory
from .intergalactica import Earthling, Reminder, TemporaryVoiceChannel, TemporaryChannel, RedditAdvertisement
from .settings import Settings, NamedEmbed, NamedChannel, Translation, Locale
from .ticket import Ticket, Reply
from .poll import Change, Parameter, Poll, PollTemplate, Vote, Option
from .scene import Scene, Scenario
from .pigeon import Pigeon, PigeonRelationship, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile
from .admin import SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word
from .prank import NicknamePrank, Prankster, EmojiPrank, RolePrank
from .reddit import Subreddit
from .qotd import Category, Question, CategoryChannel, QuestionConfig
from .intergalactica import MentionGroup, MentionMember
from .farming import Farm, Crop, FarmCrop
from .conversation import Conversant, Conversation, Participant
from .conversions import Currency, Measurement, StoredUnit

database = BaseModel._meta.database

def setup():
    with database.connection_context():
        # database.drop_tables([Conversant, Participant, Conversation])
        database.create_tables([Conversant, Participant, Conversation])

        # database.drop_tables([Currency, Measurement])
        database.create_tables([Currency, Measurement])

        # database.drop_tables([Farm, Crop, FarmCrop])
        database.create_tables([Farm, Crop, FarmCrop])

        # database.drop_tables([MentionGroup, MentionMember])
        database.create_tables([MentionGroup, MentionMember])

        # database.drop_tables([Category, Question, CategoryChannel, QuestionConfig])
        database.create_tables([Category, Question, CategoryChannel, QuestionConfig])

        # database.drop_tables([Pigeon, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, PigeonRelationship, Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile])
        database.create_tables([Pigeon, PigeonDatingParticipant, PigeonDatingAvatar, PigeonDatingRelationship, PigeonRelationship, Buff, PigeonBuff, Fight, Exploration, Mail, LanguageMastery, SystemMessage, Date, PigeonDatingProfile])

        # database.drop_tables([SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word])
        database.create_tables([SavedEmoji, Location, Giveaway, DailyReminder, PersonalQuestion, Word])

        # database.drop_tables([Subreddit])
        database.create_tables([Subreddit])

        # database.drop_tables([NicknamePrank, Prankster, EmojiPrank, RolePrank])
        database.create_tables([NicknamePrank, Prankster, EmojiPrank, RolePrank])

        # database.drop_tables([Scene, Scenario])
        database.create_tables([Scene, Scenario])

        # database.drop_tables([Human, Item, HumanItem, ItemCategory])
        database.create_tables([Human, Item, HumanItem, ItemCategory])

        # database.drop_tables([Earthling, TemporaryChannel, Reminder, TemporaryVoiceChannel, RedditAdvertisement])
        database.create_tables([Earthling, TemporaryChannel, Reminder, TemporaryVoiceChannel, RedditAdvertisement])

        # database.drop_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])
        database.create_tables([Settings, NamedEmbed, NamedChannel, Locale, Translation])

        # database.drop_tables([Ticket, Reply])
        database.create_tables([Ticket, Reply])

        # database.drop_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])
        database.create_tables([Change, Parameter, Poll, PollTemplate, Option, Vote])

setup()