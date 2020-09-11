from .base import BaseModel
from .models import Translation, NamedEmbed
from .profile import Human, GlobalHuman, RankRole, Settings, EmojiUsage
from .poll import Poll, Vote, Option
database = Human._meta.database

with database:
    database.create_tables([Translation, NamedEmbed])
    database.create_tables([Human, GlobalHuman, RankRole, Settings, EmojiUsage])
    
    database.create_tables([Poll, Option, Vote])

# from .migration import migrate_members
# migrate_members()
