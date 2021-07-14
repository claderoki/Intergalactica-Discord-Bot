import datetime

import discord
from discord.ext import commands, tasks

from src.discord.helpers.converters import EnumConverter
from src.models import Ticket, Reply, database
import src.config as config
from src.discord.cogs.core import BaseCog

class TicketCog(BaseCog, name = "Ticket"):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.command()
    @commands.dm_only()
    async def concern(self, ctx, *, concern):
        guild = self.bot.get_guild(742146159711092757)
        member = guild.get_member(ctx.author.id)

        if member is None:
            return
        #TODO: hardcoded channel.
        channel = guild.get_channel(863775516998107186)

        anonymous = True
        ticket = Ticket.create(
            text       = concern,
            user_id    = member.id,
            channel_id = channel.id,
            anonymous  = anonymous,
            type       = Ticket.Type.concern,
            guild_id   = guild.id
        )
        await ticket.sync_message(channel)

    @commands.command()
    async def reply(self, ctx, ticket : Ticket, *, response):

        if ctx.channel.type == discord.ChannelType.private:
            if ticket.user_id == ctx.author.id:
                type = Reply.Type.author
            else:
                await ctx.send(ctx.translate("not_your_ticket"))
                return
        else:
            if not ctx.author.guild_permissions.administrator:
                raise commands.errors.MissingPermissions(["administrator"])
            type = Reply.Type.staff

        if ticket.status == ticket.Status.closed:
            return await ctx.send(ctx.translate("ticket_closed"))

        attachments = ctx.message.attachments
        if len(attachments) > 0:
            for attachment in attachments:
                response += f"\n{attachment.url}"

        Reply.create(
            anonymous = ticket.anonymous,
            user_id   = ctx.author.id,
            text      = response,
            ticket    = ticket,
            type      = type
        )
        await ticket.sync_message()

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def close(self, ctx, ticket : Ticket, *, response = None):
        attachments = ctx.message.attachments
        if len(attachments) > 0:
            response = ""
            for attachment in attachments:
                response += f"\n{attachment.url}"

        if response:
            Reply.create(
                anonymous = ticket.anonymous,
                user_id   = ctx.author.id,
                text      = response,
                ticket    = ticket,
                type      = Reply.Type.staff
            )

        ticket.status = Ticket.Status.closed
        ticket.close_reason = Ticket.CloseReason.resolved
        await ticket.sync_message()

def setup(bot):
    bot.add_cog(TicketCog(bot))