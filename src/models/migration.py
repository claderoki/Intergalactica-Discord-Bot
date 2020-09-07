import peewee

import src.config as config
from .profile import OldShit as OldMember, GlobalHuman, Human


def migrate_members():
    for member in OldMember:
        human, _ = Human.get_or_create_for_oldshit(member)

        human.city      = member.city
        human.timezone  = member.timezone
        human.personal_role_id      = member.personal_role_id
        human.date_of_birth  = member.date_of_birth
        human.save()



    print("migration complete")