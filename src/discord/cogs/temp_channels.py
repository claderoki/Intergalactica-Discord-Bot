import asyncio
import datetime

import discord
from discord.ext.commands.errors import MissingPermissions

import src.discord.helpers.pretty as pretty
import src.config as config
from discord.ext import commands, tasks
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers.waiters import IntWaiter, TimeDeltaWaiter
from src.discord.helpers.checks import specific_guild_only
from src.models import (TemporaryChannel, HumanItem, Item, database)


class TempChannelsCog(BaseCog, name = "Milkyway"):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.temp_channel_checker, check = self.bot.production)

    def get_human_item(self, user, code = None, raise_on_empty = True):
        #TODO: optimize
        human_item = HumanItem.get_or_none(
            human = config.bot.get_human(user = user),
            item = Item.get(code = code)
        )
        if human_item is None or (human_item.amount == 0 and raise_on_empty):
            raise SendableException(self.bot.translate("no_" + code))
        return human_item

    @commands.max_concurrency(1, per = commands.BucketType.user)
    @commands.group(aliases = ["milkyway", "orion"])
    async def temporary_channel(self, ctx):
        ctx.admins = ctx.guild.id in (842154624869859368, 729843647347949638)
        if not ctx.admins and ctx.guild.id != 742146159711092757:
            raise SendableException("no")

        mini = ctx.invoked_with != "milkyway"
        ctx.type = TemporaryChannel.Type.mini if mini else TemporaryChannel.Type.normal

    async def create_pending(self, temp_channel: TemporaryChannel, expiry_date: datetime.datetime = None):
        if expiry_date is None:
            temp_channel.set_expiry_date(
                datetime.timedelta(days = temp_channel.days * temp_channel.pending_items)
            )
        else:
            temp_channel.set_expiry_date(expiry_date)

        temp_channel.pending_items = 0
        await temp_channel.create_channel()
        temp_channel.status = TemporaryChannel.Status.accepted
        temp_channel.save()

    @commands.has_guild_permissions(administrator = True)
    @temporary_channel.command(name = "accept")
    async def temporary_channel_accept(self, ctx, temp_channel : TemporaryChannel):
        if temp_channel.status != TemporaryChannel.Status.pending:
            raise SendableException(ctx.translate("temp_channel_not_pending"))
        if not temp_channel.active:
            raise SendableException(ctx.translate("temp_channel_not_active"))
        await self.create_pending(temp_channel)
        try:
            await temp_channel.user.send(f"Your request for a temporary channel was accepted.")
        except:
            pass
        asyncio.gather(ctx.success())

    @commands.has_guild_permissions(administrator = True)
    @temporary_channel.command(name = "deny")
    async def temporary_channel_deny(self, ctx, temp_channel : TemporaryChannel, *, reason):
        if temp_channel.status != TemporaryChannel.Status.pending:
            raise SendableException(ctx.translate("temp_channel_not_pending"))
        if not temp_channel.active:
            raise SendableException(ctx.translate("temp_channel_not_active"))

        temp_channel.status = TemporaryChannel.Status.denied
        temp_channel.active = False
        temp_channel.deny_reason = reason
        human_item = self.get_human_item(temp_channel.user, code = temp_channel.item_code, raise_on_empty = False)
        human_item.amount += temp_channel.pending_items
        human_item.save()
        temp_channel.save()
        try:
            await temp_channel.user.send(f"Your request for a temporary channel was denied. Reason: `{temp_channel.deny_reason}`\nThe item(s) spent on this will be given back.")
        except:
            pass
        asyncio.gather(ctx.success())

    @commands.has_guild_permissions(administrator = True)
    @temporary_channel.command(name = "pending")
    async def temporary_channel_pending(self, ctx):
        all_pending = TemporaryChannel\
            .select()\
            .where(TemporaryChannel.guild_id == ctx.guild.id)\
            .where(TemporaryChannel.status == TemporaryChannel.Status.pending)\
            .where(TemporaryChannel.type == ctx.type)

        for pending in all_pending:
            await ctx.send(embed = pending.ticket_embed)

    @temporary_channel.command(name = "create")
    async def temporary_channel_create(self, ctx):
        if ctx.admins:
            if not ctx.author.guild_permissions.administrator:
                raise MissingPermissions(["administrator"])

        TEMP_CHANNEL_LIMIT = 10

        amount = TemporaryChannel\
            .select()\
            .where(TemporaryChannel.guild_id == ctx.guild.id)\
            .where(TemporaryChannel.active == True)\
            .where(TemporaryChannel.status == TemporaryChannel.Status.accepted)\
            .count()

        if amount >= TEMP_CHANNEL_LIMIT:
            raise SendableException(ctx.translate("too_many_temporary_channels_active"))

        temp_channel      = TemporaryChannel(
            guild_id      = ctx.guild.id,
            user_id       = ctx.author.id,
            type          = ctx.type,
            pending_items = 1
        )

        if not ctx.admins:
            human_item = self.get_human_item(ctx.author, code = temp_channel.item_code)

            if human_item.amount > 1:
                waiter = IntWaiter(ctx, prompt = ctx.translate(f"{temp_channel.item_code}_count_prompt"), min = 1, max = human_item.amount)
                items_to_use = await waiter.wait()
            else:
                items_to_use = 1

            temp_channel.pending_items = items_to_use

            human_item.amount -= items_to_use
            human_item.save()

        await temp_channel.editor_for(ctx, "name")
        await temp_channel.editor_for(ctx, "topic")

        if ctx.admins:
            waiter = TimeDeltaWaiter(ctx)
            await self.create_pending(temp_channel, expiry_date = await waiter.wait())
        else:
            await ctx.send("A request has been sent to the staff.")
            temp_channel.save()
            await ctx.guild.get_channel(863775783940390912).send(embed = temp_channel.ticket_embed)

    @temporary_channel.command(name = "extend")
    async def temporary_channel_extend(self, ctx, channel : discord.TextChannel):
        try:
            temp_channel = TemporaryChannel.get(channel_id = channel.id, guild_id = ctx.guild.id)
        except TemporaryChannel.DoesNotExist:
            raise SendableException(ctx.translate("temp_channel_not_found"))

        if not ctx.admins:
            human_item = self.get_human_item(ctx.author, code = temp_channel.item_code)

            if human_item.amount > 1:
                waiter = IntWaiter(ctx, prompt = ctx.translate("temporary_channel_count_prompt"), min = 1, max = human_item.amount)
                items_to_use = await waiter.wait()
            else:
                items_to_use = 1

            temp_channel.set_expiry_date(datetime.timedelta(days = temp_channel.days * items_to_use))
            asyncio.gather(temp_channel.update_channel_topic())
            human_item.amount -= items_to_use
            human_item.save()
            temp_channel.save()
        else:
            waiter = TimeDeltaWaiter(ctx)
            temp_channel.set_expiry_date(await waiter.wait())
            asyncio.gather(temp_channel.update_channel_topic())

        await ctx.send(f"Okay. This channel has been extended until `{temp_channel.expiry_date}`")

    @temporary_channel.command(name = "history")
    async def temporary_channel_history(self, ctx):
        query = TemporaryChannel.select()
        query = query.where(TemporaryChannel.type == ctx.type)
        query = query.where(TemporaryChannel.active == False)
        query = query.where(TemporaryChannel.status == TemporaryChannel.Status.accepted)
        query = query.where(TemporaryChannel.guild_id == ctx.guild.id)

        data = []
        data.append(("name", "creator"))
        for channel in query:
            data.append((channel.name, pretty.limit_str(channel.user, 10)))

        table = pretty.Table.from_list(data, first_header = True)
        await table.to_paginator(ctx, 10).wait()

    @tasks.loop(hours = 1)
    async def temp_channel_checker(self):
        with database.connection_context():
            query = TemporaryChannel.select(TemporaryChannel.id, TemporaryChannel.guild_id, TemporaryChannel.channel_id, TemporaryChannel.active)
            query = query.where(TemporaryChannel.active == True)
            query = query.where(TemporaryChannel.expiry_date != None)
            query = query.where(TemporaryChannel.expiry_date <= datetime.datetime.utcnow())
            for temp_channel in query:
                channel = temp_channel.channel
                temp_channel.active = False
                if channel is not None:
                    try:
                        await channel.delete(reason = "Expired")
                    except:
                        pass
                temp_channel.channel_id = None
                temp_channel.save()

def setup(bot):
    bot.add_cog(TempChannelsCog(bot))
