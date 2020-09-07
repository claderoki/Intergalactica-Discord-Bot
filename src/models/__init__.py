from .base import BaseModel
from .models import Translation
from .profile import Human, GlobalHuman, RankRole, Settings, Rule, EmojiUsage
from .poll import Poll, Vote, Option
database = Human._meta.database

with database:
    # database.drop_tables([Human, GlobalHuman])
    database.create_tables([Human, Translation, GlobalHuman, RankRole, Settings, Rule, EmojiUsage])

    
    database.create_tables([Poll, Option, Vote])
# from .migration import migrate_members
# migrate_members()