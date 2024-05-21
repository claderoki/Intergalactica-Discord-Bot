import asyncio

import discord
from discord.ext import commands

from src.disc.cogs.custom.shared.cog import CustomCog
from src.disc.helpers.known_guilds import KnownGuild
from src.models.crossroad import StarboardMapping


class KnownChannel:
    starboard = 1115301555504160790 # 1014293774119215154 # 1115301555504160790


class MessageLink(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label='Go to Message', url=url, style=discord.ButtonStyle.link))


class Crossroad(CustomCog):
    guild_id = KnownGuild.crossroads

    _threshold = 1
    _mapping = {}
    _in_progress = set()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if self.bot.production and self.guild_id == KnownGuild.proboscis:
            return
        if not self.bot.production and self.guild_id == KnownGuild.crossroads:
            return

        if payload.guild_id != self.guild_id:
            return
        if str(payload.emoji) != '⭐':
            return
        if payload.channel_id == KnownChannel.starboard:
            return
        # wait 5 mins or until in progress is removed.
        if payload.message_id in self._in_progress:
            for _ in range(5):
                await asyncio.sleep(60)
                print('payload.message_id in self._in_progress 60 sec sleep')
                if payload.message_id not in self._in_progress:
                    print('payload.message_id not in self._in_progress break')
                    break

        self._in_progress.add(payload.message_id)
        try:
            await self._process(payload)
        except Exception as e:
            print('Crossroad::on_raw_reaction_add', e)
            raise e
        finally:
            self._in_progress.remove(payload.message_id)

    async def _process(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(self.guild_id)
        from_channel = guild.get_channel(payload.channel_id)

        message: discord.Message = await from_channel.fetch_message(payload.message_id)
        reaction = None
        for r in message.reactions:
            if str(r.emoji) == str(payload.emoji):
                reaction = r
                break
        users = []
        async for user in reaction.users():
            if not user.bot and user.id != message.author.id:
                users.append(user)

        bot_message_id = self._mapping.get(payload.message_id)
        bot_channel = guild.get_channel(KnownChannel.starboard)
        if bot_channel is None:
            print('bot_channel is none')
            return
        try:
            bot_message = await bot_channel.fetch_message(bot_message_id) if bot_message_id else None
        except:
            try:
                StarboardMapping.delete().where(StarboardMapping.user_message_id == message.id).execute()
            except Exception as e:
                print('StarboardMapping.delete().where(StarboardMapping.user_message_id == message.id)', e)
            bot_message = None
        if bot_message is None and len(users) >= self._threshold:
            description = []
            if message.reference is not None:
                reference = await from_channel.fetch_message(message.reference.message_id)
                description.append(f'> **Replying to {reference.author.name}**')
                description.append(f'> {reference.content}')
                description.append('')

            description.append(message.content) # probably include images too
            embed = discord.Embed(description='\n'.join(description))
            embed.set_author(name=str(message.author.name), icon_url=message.author.display_avatar)
            embed.set_footer(text=f'#{from_channel.name} | {message.created_at.strftime("%Y-%m-%d %H:%M")}')

            bot_message = await bot_channel.send(f'⭐ {len(users)}', embed=embed, view=MessageLink(message.jump_url))

            StarboardMapping.create(guild_id=payload.guild_id,
                                    user_message_id=message.id,
                                    bot_message_id=bot_message.id)
            self._mapping[message.id] = bot_message.id
            return

        if bot_message is not None:
            content = f'⭐ {len(users)}'
            if content != bot_message.content:
                await bot_message.edit(content=content)

    @commands.Cog.listener()
    async def on_ready(self):
        for mapping in StarboardMapping.select().where(StarboardMapping.guild_id == self.guild_id):
            self._mapping[mapping.user_message_id] = mapping.bot_message_id


async def setup(bot):
    await bot.add_cog(Crossroad(bot))
