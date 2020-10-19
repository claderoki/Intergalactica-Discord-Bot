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

emoji_match = lambda x : [int(x) for x in re.findall(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>', x)]

def increment_emoji(guild, emoji):
    with database:
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

        if payload.member.bot or emoji.id is None:
            return

        member = payload.member

        if emoji in member.guild.emojis:
            increment_emoji(member.guild, emoji)

    @commands.command()
    async def emojis(self, ctx, order = "least"):
        emoji_usages = [x for x in EmojiUsage.select().where(EmojiUsage.guild_id == ctx.guild.id).order_by(EmojiUsage.total_uses.desc()) if x.emoji is not None]
        first = -10 if order == "least" else 0
        last = -1 if order == "least" else 10

        emoji_ids = [x.emoji_id for x in emoji_usages]

        with database:
            for emoji in ctx.guild.emojis:
                if emoji.id is not None:
                    if emoji.id not in emoji_ids:
                        emoji_usages.append( EmojiUsage.create(guild_id = ctx.guild.id, emoji_id = emoji.id) )

            embed = discord.Embed(color = ctx.guild_color )
            embed.description = ""

            for usage in emoji_usages[first:last]:
                embed.description += f"{usage.emoji} = {usage.total_uses}\n"

            await ctx.send(embed = embed)

    # @commands.command()
    # @commands.is_owner()
    # async def selfie(self, ctx):
    #     await ctx.message.delete()
    #     response = requests.get("http://www.mwctoys.com/images2/review_ssc3po_3.jpg", stream=True)
    #     f = io.BytesIO(response.raw.read())
    #     msg = await ctx.send(file=discord.File(fp=f, filename="selfie.jpg", spoiler = True))

    @commands.has_guild_permissions(administrator = True)
    @commands.group()
    async def channel(self, ctx):
        pass

    @channel.command(name = "set")
    async def channel_set(self, ctx, name : str, channel : discord.TextChannel):
        with database:
            named_channel, created = NamedChannel.get_or_create(name = name, settings = ctx.settings)
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
        with database:
            try:
                Translation.create(message_key = key, value = value)
            except:
                asyncio.gather(ctx.error())
            else:
                asyncio.gather(ctx.success())

    @translation.command()
    async def keys(self, ctx, locale : Locale = "en_US"):
        missing_translations = self.bot.missing_translations.get(locale.name, [])
        with database:
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

        with database:
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
        with database:
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