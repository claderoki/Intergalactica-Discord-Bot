import asyncio
import random

import discord

from src.config import config
from src.models import GameRole, GameRoleSettings


class RoleHelper:
    @classmethod
    async def create(cls, guild: discord.Guild, *args, position: int = None, **kwargs) -> discord.Role:
        """Creates a role and returns it; is basically the same as disc.Guild.create_role but also supports
        position. """
        role = await guild.create_role(*args, **kwargs)
        if position is not None:
            try:
                # for some reason editing a role once doesn't always move it properly.
                await role.edit(position=position)
                await role.edit(position=position)
                await role.edit(position=position)
            except:
                pass
        return role


class GameRoleProcessor:
    __slots__ = ("guild", "mapping", "settings", "data")

    def __init__(self, settings: GameRoleSettings):
        self.settings = settings
        self.data = {}
        self.guild = config.bot.get_guild(settings.guild_id)
        self.__load_mapping()

    def __get_role_id(self, game_name: str) -> int:
        for name, role_id in self.mapping.items():
            if name.lower() == game_name.lower():
                return role_id

    def get_role(self, game_name: str) -> discord.Role:
        role_id = self.__get_role_id(game_name)
        if role_id is None:
            return None

        return self.guild.get_role(role_id)

    def __get_random_role(self) -> discord.Role:
        if len(self.mapping) == 0:
            return None

        role_ids = list(self.mapping.values())

        for _ in range(5):
            if len(role_ids) == 0:
                return None

            role_id = random.choice(role_ids)
            role_ids.remove(role_id)
            role = self.guild.get_role(role_id)
            if role is not None:
                return role

    def __get_position(self) -> int:
        role = self.__get_random_role()
        if role is not None:
            return role.position
        else:
            return 1

    def __load_mapping(self):
        self.mapping = {}
        for game_role in GameRoleRepository.get_all_for_guild(self.guild.id):
            self.mapping[game_role.game_name] = game_role.role_id

    def log(self, message: str):
        if self.settings.log_channel_id is not None:
            asyncio.gather(self.guild.get_channel(self.settings.log_channel_id).send(message))

    def __cleanup_role(self, role_id: int, game_name: str):
        """Cleans up a specific role from the db & cache."""
        GameRoleRepository.remove(self.guild.id, role_id, game_name)
        del self.mapping[game_name]

    async def cleanup(self):
        """Removes roles in the db & cache that no longer exist."""
        for game_name in list(self.mapping.keys()):
            role_id = self.mapping[game_name]
            role = self.guild.get_role(role_id)
            if role is None:
                self.__cleanup_role(role_id, game_name)
            elif len(role.members) < self.settings.threshhold:
                await role.delete()
                self.log("Cleaned up " + game_name)
                self.__cleanup_role(role_id, game_name)

    async def __process_new(self, member: discord.Member, game: discord.Game):
        user_ids = self.data.setdefault(game.name, set())
        user_ids.add(member.id)
        if len(user_ids) >= self.settings.threshhold:
            role = await RoleHelper.create(member.guild, name=game.name, position=self.__get_position(), mentionable=True)
            self.mapping[game.name] = role.id
            GameRoleRepository.save(self.guild.id, role.id, game.name)
            for user_id in user_ids:
                other_member = member.guild.get_member(user_id)
                if other_member is not None:
                    await other_member.add_roles(role)
            del self.data[game.name]
            self.log(f"`{game.name}` role created.")

    async def __process_existing(self, member: discord.Member, game: discord.Game):
        role_id = self.mapping[game.name]
        role = member.guild.get_role(role_id)
        if role is None:
            self.__cleanup_role(role_id, game.name)
            return await self.__process_new(member, game)

        await member.add_roles(role)

    async def process(self, member: discord.Member, game: discord.Game):
        if game is None:
            return

        if game.name in self.mapping:
            await self.__process_existing(member, game)
        else:
            await self.__process_new(member, game)


class GameRoleRepository:
    @classmethod
    def save(cls, guild_id: int, role_id: int, game_name: str):
        try:
            GameRole.create(guild_id=guild_id, role_id=role_id, game_name=game_name)
        except Exception as e:
            print("Exception GameRoleRepository::save", e)
            pass

    @classmethod
    def remove(cls, guild_id: int, role_id: int, game_name: str):
        try:
            GameRole.delete().where(GameRole.guild_id == guild_id).where(GameRole.role_id == role_id).where(
                GameRole.game_name == game_name).execute()
        except Exception as e:
            print("Exception GameRoleRepository::remove", e)
            pass

    @classmethod
    def get_all_for_guild(cls, guild_id: int) -> list:
        return list(GameRole.select().where(GameRole.guild_id == guild_id))

    @classmethod
    def get_settings(cls, guild_id: int) -> GameRoleSettings:
        return GameRoleSettings.get_or_none(guild_id=guild_id)

    @classmethod
    def get_all_settings(cls) -> list:
        return list(GameRoleSettings.select().where(GameRoleSettings.enabled == True))
