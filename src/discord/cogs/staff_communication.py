import datetime

import discord
from discord.ext import commands, tasks

from src.models import Ticket, Reply, database as db
import src.config as config

class StaffCommunication(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        pass


    @commands.Cog.listener()
    async def on_message(self, message):
        pass


    async def create_ticket(self, user, guild, type):
        guild = self.bot.get_guild(742146159711092757)
        member = guild.get_member(ctx.author.id)

        if member is None:
            return

        channel = guild.get_channel(758296826549108746)

        anonymous = True
        with db:
            ticket = Ticket.create(text = concern, user_id = member.id, anonymous = anonymous, type = Ticket.Type.concern, guild_id = guild.id)
            await ticket.sync_message(channel)



    @commands.command()
    @commands.dm_only()
    async def concern(self, ctx, *, concern):
        guild = await self.bot.guild_choice_for(ctx.author)
        member = guild.get_member(ctx.author.id)

        if member is None:
            return

        channel = guild.get_channel(758296826549108746)

        anonymous = True
        with db:
            ticket = Ticket.create(text = concern, user_id = member.id, channel_id = channel.id, anonymous = anonymous, type = Ticket.Type.concern, guild_id = guild.id)
            await ticket.sync_message(channel)

    @commands.command()
    async def reply(self, ctx, ticket : Ticket, *, response):

        if ctx.channel.type == discord.ChannelType.private:
            if ticket.user_id == ctx.author.id:
                type = Reply.Type.author
            else:
                await ctx.send("This is not your ticket!")
                return
        else:
            if not ctx.author.guild_permissions.administrator:
                raise commands.errors.MissingPermissions(["administrator"])
            type = Reply.Type.staff

        attachments = ctx.message.attachments
        if len(attachments) > 0:
            for attachment in attachments:
                response += f"\n{attachment.url}"


        with db:
            reply = Reply.create(anonymous = ticket.anonymous, user_id = ctx.author.id, text = response, ticket = ticket, type = type)
            await ticket.sync_message()


def setup(bot):
    bot.add_cog(StaffCommunication(bot))