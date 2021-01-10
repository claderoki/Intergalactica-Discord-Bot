import re
import json
import io
import asyncio

import requests
import discord
from discord.ext import commands

import src.config as config
from src.models import Settings, EmojiUsage, NamedEmbed, NamedChannel, Translation, Locale, database
from src.discord.helpers.waiters import *
from src.discord.errors.base import SendableException

emoji_match = lambda x : [int(x) for x in re.findall(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>', x)]

def increment_emoji(guild, emoji):
    with database.connection_context():
        usage, _ = EmojiUsage.get_or_create(guild_id = guild.id, emoji_id = emoji.id)
        usage.total_uses += 1
        usage.save()

class Management(discord.ext.commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return

        if message.author.bot:
            return

        ids = emoji_match(message.content)
        for id in ids:
            emoji = self.bot.get_emoji(id)
            if emoji in message.guild.emojis:
                increment_emoji(message.guild, emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not self.bot.production:
            return

        emoji = payload.emoji
        member = payload.member

        if member is None or member.bot or emoji.id is None:
            return

        if emoji in member.guild.emojis:
            increment_emoji(member.guild, emoji)

    @commands.command()
    async def emojis(self, ctx, order = "least", animated : bool = False):
        query = EmojiUsage.select()
        query = query.where(EmojiUsage.guild_id == ctx.guild.id)
        if order == "least":
            query = query.order_by(EmojiUsage.total_uses.asc())
        else:
            query = query.order_by(EmojiUsage.total_uses.desc())

        emoji_usages = [x for x in query if x.emoji is not None and x.emoji.animated == animated]

        emoji_ids = [x.emoji_id for x in emoji_usages]

        for emoji in ctx.guild.emojis:
            if emoji.id is not None:
                if emoji.id not in emoji_ids:
                    try:
                        emoji_usages.append( EmojiUsage.create(guild_id = ctx.guild.id, emoji_id = emoji.id) )
                    except: pass
            else:
                if emoji.id in emoji_ids:
                    usage = EmojiUsage.get(emoji_id = emoji.id, guild_id = ctx.guild.id)
                    usage.delete_instance()

        embed = discord.Embed(color = ctx.guild_color )

        lines = []

        for usage in emoji_usages[:10]:
            line = f"{usage.emoji} = {usage.total_uses}"
            if order == "least":
                lines.insert(0, line)
            else:
                lines.append(line)

        embed.description = "\n".join(lines)
        await ctx.send(embed = embed)

    @commands.has_guild_permissions(administrator = True)
    @commands.group()
    async def channel(self, ctx):
        pass

    @channel.command(name = "set")
    async def channel_set(self, ctx, name : str, channel : discord.TextChannel):
        settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
        named_channel, created = NamedChannel.get_or_create(name = name, settings = settings)
        named_channel.channel_id = channel.id
        named_channel.save()

        asyncio.gather(ctx.send("OK"))

    @commands.is_owner()
    @commands.command()
    async def stop(self, ctx):
        quit()

    @commands.is_owner()
    @commands.command()
    async def blacklist(self, ctx):
        await ctx.send("OK")

    @commands.is_owner()
    @commands.group()
    async def translation(self, ctx):
        pass

    @translation.command(name = "add")
    async def add_translation(self, ctx, key, *, value):
        try:
            Translation.create(message_key = key, value = value)
        except:
            asyncio.gather(ctx.error())
        else:
            asyncio.gather(ctx.success())

    @translation.command(name = "remove")
    async def translation_remove(self, ctx, key, locale = "en_US"):
        missing_translations = self.bot.get_missing_translations(locale)
        try:
            translation = Translation.get(message_key = key)
        except Translation.DoesNotExist:
            raise SendableException(ctx.translate("key_not_found"))

        translation.delete_instance()
        missing_translations.add(key)
        asyncio.gather(ctx.success())

    @translation.command()
    async def keys(self, ctx, locale = "en_US"):
        missing_translations = self.bot.get_missing_translations(locale)
        for key in [x for x in missing_translations]:
            waiter = StrWaiter(ctx, prompt = f"Translate: {key}", max_words = None, skippable = True)
            try:
                value = await waiter.wait()
            except Skipped:
                return
            else:
                Translation.create(message_key = key, value = value, locale = locale)
                missing_translations.remove(key)

        asyncio.gather(ctx.send(ctx.translate("keys_created")))

    @translation.command()
    async def fromen(self, ctx, locale : Locale):
        if locale.name == "en_US":
            return await ctx.send("wtf?")

        translations = list( Translation.select().where(Translation.locale.in_([locale, "en_US"])).order_by(Translation.locale.desc()) )

        locale_translations = [x.message_key for x in translations if x.locale.name == locale]
        for translation in [x for x in translations if x.locale.name == "en_US"]:
            if translation.message_key not in locale_translations:

                waiter = StrWaiter(ctx, prompt = f"Translate: `{translation.value}`", max_words = None, skippable = True)
                try:
                    value = await waiter.wait()
                except Skipped:
                    return
                else:
                    Translation.create(message_key = translation.message_key, value = value, locale = locale)

        asyncio.gather(ctx.send(ctx.translate("translations_created")))

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def embed(self, ctx, name):
        settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)

        if len(ctx.message.attachments) > 0:
            attachment = ctx.message.attachments[0]
            data = json.loads(await attachment.read())

            embed_data = data["embeds"][0]
            embed = discord.Embed.from_dict(embed_data)
            await ctx.send(embed = embed)

            named_embed, _ = NamedEmbed.get_or_create(name = name, settings = settings)
            named_embed.data = embed_data
            named_embed.save()
        else:
            try:
                named_embed = NamedEmbed.get(name = name, settings = settings)
            except NamedEmbed.DoesNotExist:
                await ctx.send("This embed does not exist")
            else:
                await ctx.send(embed = named_embed.embed)

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def resetchannel(self, ctx, channel : discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        await channel.clone()
        await channel.delete()

def setup(bot):
    bot.add_cog(Management(bot))