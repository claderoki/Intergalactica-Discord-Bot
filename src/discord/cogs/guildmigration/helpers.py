import discord
import requests


class GuildMigration:
    __slots__ = ("role_mapping", "channel_mapping", "template", "to", "log_channel")

    def __init__(self, template: discord.Guild, to: discord.Guild, log_channel: discord.TextChannel):
        self.role_mapping = {}
        self.channel_mapping = {}
        self.template = template
        self.to = to
        self.log_channel = log_channel

    async def __migrate_roles(self):
        for role in self.template.roles[::-1]:
            if role == self.template.default_role:
                self.role_mapping[role.id] = self.to.default_role
                continue

            if role.managed or role.is_integration() or role.is_bot_managed() or role.is_premium_subscriber():
                continue

            new = await self.to.create_role(
                name=role.name,
                permissions=role.permissions,
                colour=role.colour,
                hoist=role.hoist,
                mentionable=role.mentionable,
            )
            self.role_mapping[role.id] = new

    def __copy_overwrites(self, overwrites: dict):
        new = {}
        for obj, overwrite in overwrites.items():
            if isinstance(obj, discord.Role):
                role = self.role_mapping.get(obj.id)
                if role is not None:
                    new[role] = overwrite
        return new

    async def __migrate_categories(self):
        for category in self.template.categories:
            overwrites = self.__copy_overwrites(category.overwrites)
            new = await self.to.create_category(
                name=category.name,
                overwrites=overwrites,
                position=category.position,
            )
            self.channel_mapping[category.id] = new

    async def __migrate_emojis(self):
        for emoji in self.template.emojis:
            if emoji.managed:
                continue

            roles = None
            if emoji.roles is not None:
                roles = list(filter(None, [self.role_mapping.get(x.id) for x in emoji.roles]))
            raw = requests.get(emoji.url, stream=True).raw.read()

            await self.to.create_custom_emoji(
                name=emoji.name,
                roles=roles,
                image=raw
            )

    async def __migrate_channels(self):
        for channel in self.template.channels:
            kwargs = {}
            keys = ["name", "position"]

            if isinstance(channel, discord.TextChannel):
                create_channel = self.to.create_text_channel
                keys.extend(["topic", "slowmode_delay", "nsfw"])
            elif isinstance(channel, discord.VoiceChannel):
                create_channel = self.to.create_voice_channel
                keys.extend(["bitrate", "user_limit", "rtc_region"])
            else:
                continue

            kwargs["overwrites"] = self.__copy_overwrites(channel.overwrites)
            if channel.category is not None:
                kwargs["category"] = self.channel_mapping.get(channel.category.id)

            for key in keys:
                kwargs[key] = getattr(channel, key)

            new = await create_channel(**kwargs)
            self.channel_mapping[channel.id] = new

    async def migrate(self):
        await self.log_channel.send("Migrating roles...")
        async with self.log_channel.typing():
            await self.__migrate_roles()

        await self.log_channel.send("Migrating categories...")
        async with self.log_channel.typing():
            await self.__migrate_categories()

        await self.log_channel.send("Migrating channels...")
        async with self.log_channel.typing():
            await self.__migrate_channels()

        # await self.log_channel.send("Migrating emojis...")
        # async with self.log_channel.typing():
        #     await self.__migrate_emojis()

        await self.log_channel.send("Migration successful.")
