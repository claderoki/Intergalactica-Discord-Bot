from src.models.base import RoleIdField, GuildSettings, MemberProfile


class PersonalRoleSettings(GuildSettings):
    required_role_id = RoleIdField(null=True)


class PersonalRoleProfile(MemberProfile):
    role_id = RoleIdField(null=False)
