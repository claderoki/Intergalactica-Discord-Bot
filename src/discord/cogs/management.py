from discord.ext import commands

from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers.general import Translator
from src.discord.helpers.waiters import *
from src.models import Translation, Locale


class Management(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.is_owner()
    @commands.command()
    async def stop(self, ctx):
        quit()

    @commands.is_owner()
    @commands.command(aliases=["daizy"])
    async def cooldown(self, ctx, user: discord.User):
        if user.id in ctx.bot.cooldowned_users:
            ctx.bot.cooldowned_users.remove(user.id)
        else:
            ctx.bot.cooldowned_users.append(user.id)
        await ctx.send("OK")

    @commands.is_owner()
    @commands.group()
    async def translation(self, ctx):
        pass

    @translation.command(name="add")
    async def add_translation(self, ctx, key, *, value):
        try:
            Translation.create(message_key=key, value=value)
        except:
            asyncio.gather(ctx.error())
        else:
            asyncio.gather(ctx.success())

    @translation.command(name="remove")
    async def translation_remove(self, ctx, key, locale="en_US"):
        missing_translations = Translator.get_missing(locale)
        try:
            translation = Translation.get(message_key=key)
        except Translation.DoesNotExist:
            raise SendableException(ctx.translate("key_not_found"))

        translation.delete_instance()
        missing_translations.add(key)
        asyncio.gather(ctx.success())

    @translation.command()
    async def keys(self, ctx, locale="en_US"):
        missing_translations = Translator.get_missing(locale)
        for key in [x for x in missing_translations]:
            waiter = StrWaiter(ctx, prompt=f"Translate: {key}", max_words=None, skippable=True)
            try:
                value = await waiter.wait()
            except Skipped:
                return
            else:
                Translation.create(message_key=key, value=value, locale=locale)
                missing_translations.remove(key)

        asyncio.gather(ctx.send(ctx.translate("keys_created")))

    @translation.command()
    async def fromen(self, ctx, locale: Locale):
        if locale.name == "en_US":
            return await ctx.send("wtf?")

        query = Translation.select()
        query = query.where(Translation.locale.in_([locale, "en_US"]))
        query = query.order_by(Translation.locale.desc())

        translations = list(query)
        locale_translations = [x.message_key for x in translations if x.locale.name == locale.name]

        for translation in [x for x in translations if x.locale.name == "en_US"]:
            if translation.message_key not in locale_translations:
                waiter = StrWaiter(ctx, prompt=f"Translate: `{translation.value}`", max_words=None, skippable=True)
                try:
                    value = await waiter.wait()
                except Skipped:
                    return
                else:
                    Translation.create(message_key=translation.message_key, value=value, locale=locale)

        asyncio.gather(ctx.send(ctx.translate("translations_created")))

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def resetchannel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        await channel.clone()
        await channel.delete()


async def setup(bot):
    await bot.add_cog(Management(bot))
