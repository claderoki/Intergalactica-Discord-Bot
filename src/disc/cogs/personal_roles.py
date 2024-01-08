import random

import discord
from discord.ext import commands

import src.disc.helpers.pretty as pretty
from src.disc.cogs.core import BaseCog
from src.disc.errors.base import SendableException
from src.disc.helpers.colors import ColorHelper
from src.disc.helpers.condition_flow import ConditionBlock, MemberCondition, ConditionFlow, ConditionFlowValidator, \
    ValidationContext
from src.disc.helpers.known_guilds import KnownGuild
from src.models import Earthling


def _get_icon_url(obj):
    options = {"format": "png", "static_format": "png", "size": 16}
    if isinstance(obj, (discord.User, discord.ClientUser, discord.Member)):
        return obj.avatar_url_as(**options)
    elif isinstance(obj, discord.Guild):
        return obj.icon_url_as(**options)

class PersonalRoleHelper:
    __slots__ = ()

    @classmethod
    def calculate_position(cls, guild_id: int) -> int:
        first_earthling = Earthling.select().where(Earthling.personal_role_id != None).where(
            Earthling.guild_id == guild_id).first()
        if first_earthling is not None and first_earthling.personal_role is not None:
            return max(1, first_earthling.personal_role.position)
        else:
            return 1


class PersonalRoleCog(BaseCog, name="Personal role"):
    flows = {
        KnownGuild.intergalactica: ConditionFlow([
            ConditionBlock.single(MemberCondition.has_any_role(778744417322139689), 0),
            ConditionBlock.single(MemberCondition.is_nitro_booster(), 1)
        ]),
        KnownGuild.cerberus: True,
        KnownGuild.guac: True,
        KnownGuild.kail: True,
        KnownGuild.catnip: True,
        KnownGuild.mouse: ConditionFlow([
            ConditionBlock.single(MemberCondition.has_any_role(761260319820873809), 0),
            ConditionBlock.single(MemberCondition.has_any_role(761358543998681150), 0),
        ])
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
            position = PersonalRoleHelper.calculate_position(ctx.guild.id)
            role = await ctx.guild.create_role(**kwargs)
            try:
                await role.edit(position=position)
                await role.edit(position=position)
            except Exception as e:
                print(f"Couldn't move to position {position}: ", e)
                pass
            earthling.personal_role = role
            earthling.save()
            await ctx.send(ctx.bot.translate("role_created").format(role=role))
        else:
            role = earthling.personal_role
            await role.edit(**{attr_name: attr_value})
            msg = ctx.bot.translate(f"attr_added").format(name="role's " + attr_name, value=attr_value)
            embed = discord.Embed(color=role.color, title=msg)
            await ctx.send(embed=embed)

        await ctx.author.add_roles(role)

    @commands.group()
    async def role(self, ctx):
        flow = self.flows.get(ctx.guild.id)
        if flow is None:
            raise SendableException("Not allowed in this guild.")
        if flow == True:
            allowed = True
        elif isinstance(flow, ConditionFlow):
            allowed = ConditionFlowValidator.match_flow(ValidationContext.from_message(ctx.message), flow)

        if not allowed:
            first = (Earthling
                     .select(Earthling.personal_role_id)
                     .where(Earthling.guild_id == ctx.guild.id)
                     .where(Earthling.user_id == ctx.message.author.id)
                     .first()
                     )
            if first is None or first.personal_role_id is None:
                raise SendableException("You are not allowed to run this command yet.")

    @role.command(name="color", aliases=["colour"])
    async def role_color(self, ctx, color: str.lower = None):
        if color == "christmas":
            color = random.choice(('#165B33', '#146B3A', '#F8B229', '#EA4630', '#BB2528'))

        if color is None:
            color = ColorHelper.calculate_dominant_color(_get_icon_url(ctx.author))
        else:
            color = await commands.ColorConverter().convert(ctx, color)

        await self.edit_personal_role(ctx, color=color)

    @role.command(name="name")
    async def role_name(self, ctx, *, name: str):
        await self.edit_personal_role(ctx, name=name)

    @commands.is_owner()
    @role.command(name="list")
    async def role_list(self, ctx):
        query = Earthling.select(Earthling.guild_id, Earthling.personal_role_id)
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.where(Earthling.personal_role_id != None)
        roles = []
        for earthling in query:
            role = earthling.personal_role
            if role is not None:
                roles.append(role)
        roles.sort(key=lambda x: x.position)

        table = pretty.Table()
        table.add_row(pretty.Row(["role", "pos", "in use"], header=True))

        for role in roles:
            values = [role.name, role.position, len(role.members) > 0]
            table.add_row(pretty.Row(values))
        await table.to_paginator(ctx, 20).wait()

        table = pretty.Table()

    @role.command(name="delete")
    async def delete_role(self, ctx):
        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        if earthling.personal_role_id is not None:
            role = earthling.personal_role
            if role is not None:
                await role.delete()

            earthling.personal_role_id = None
            earthling.save()

            await ctx.send(ctx.bot.translate("attr_removed").format(name="role"))


async def setup(bot):
    await bot.add_cog(PersonalRoleCog(bot))
