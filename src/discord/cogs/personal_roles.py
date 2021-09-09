import asyncio
from enum import Enum

import discord
from discord.ext import commands

import src.discord.helpers.pretty as pretty
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.models import (Earthling, database)
from src.discord.helpers.condition_flow import ConditionBlock, MemberCondition, ConditionFlow, ConditionFlowValidator

class PersonalRoleHelper:
    __slots__ = ()

    @classmethod
    def calculate_position(cls) -> int:
        first_earthling = Earthling.select().where(Earthling.personal_role_id != None).first()
        if first_earthling is not None and first_earthling.personal_role is not None:
            return max(1, first_earthling.personal_role.position)
        else:
            return 1

class KnownGuild:
    intergalactica = 742146159711092757
    mouse          = 842154624869859368
    kail           = 884843718534901861

class PersonalRoleCog(BaseCog, name = "Personal role"):
    flows = {
        KnownGuild.intergalactica: ConditionFlow([
            ConditionBlock.single(MemberCondition.has_any_role(778744417322139689), 0),
            ConditionBlock.single(MemberCondition.has_any_role(742147647233720461), 1)
        ]),
        KnownGuild.mouse: True,
        KnownGuild.kail: True
    }

    def __init__(self, bot):
        super().__init__(bot)

    async def edit_personal_role(self, ctx, **kwargs):
        attr_name = ctx.command.name
        attr_value = kwargs[attr_name]

        if attr_name == "name":
            kwargs["color"] = ctx.guild_color
        elif attr_name == "color":
            kwargs["name"] = ctx.author.display_name

        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        new = earthling.personal_role is None
        if new:
            position = PersonalRoleHelper.calculate_position()
            role = await ctx.guild.create_role(**kwargs)
            try:
                await role.edit(position = position)
            except:
                pass
            earthling.personal_role = role
            earthling.save()
            await ctx.send(ctx.bot.translate("role_created").format(role = role))
        else:
            role = earthling.personal_role
            await role.edit(**{attr_name : attr_value})
            msg = ctx.bot.translate(f"attr_added").format(name = "role's " + attr_name, value = attr_value)
            embed = discord.Embed(color = role.color, title = msg)
            await ctx.send(embed = embed)

        await ctx.author.add_roles(role)

    @commands.group()
    async def role(self, ctx):
        flow = self.flows.get(ctx.guild.id)
        if flow is None:
            raise SendableException("Not allowed in this guild.")
        if flow == True:
            allowed = True
        elif isinstance(flow, ConditionFlow):
            allowed = ConditionFlowValidator.match_flow(ctx.message.author, flow)

        if not allowed:
            raise SendableException("You are not allowed to run this command yet.")

    @role.command(name = "color", aliases = ["colour"])
    async def role_color(self, ctx, color : discord.Color = None):
        if color is None:
            color = self.bot.calculate_dominant_color(self.bot._get_icon_url(ctx.author))

        await self.edit_personal_role(ctx, color = color)

    @role.command(name = "name")
    async def role_name(self, ctx, *, name : str):
        await self.edit_personal_role(ctx, name = name)

    @commands.is_owner()
    @role.command(name = "list")
    async def role_list(self, ctx):
        query = Earthling.select(Earthling.guild_id, Earthling.personal_role_id)
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.where(Earthling.personal_role_id != None)
        roles = []
        for earthling in query:
            role = earthling.personal_role
            if role is not None:
                roles.append(role)
        roles.sort(key = lambda x : x.position)

        table = pretty.Table()
        table.add_row(pretty.Row(["role", "pos", "in use"], header = True))

        for role in roles:
            values = [role.name, role.position, len(role.members) > 0]
            table.add_row(pretty.Row(values))
        await table.to_paginator(ctx, 20).wait()

        table = pretty.Table()

    @role.command(name = "delete")
    async def delete_role(self, ctx):
        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        if earthling.personal_role_id is not None:
            role = earthling.personal_role
            if role is not None:
                await role.delete()

            earthling.personal_role_id = None
            earthling.save()

            await ctx.send(ctx.bot.translate("attr_removed").format(name = "role"))

def setup(bot):
    bot.add_cog(PersonalRoleCog(bot))
