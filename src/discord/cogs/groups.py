from discord.ext import commands

import src.discord.helpers.pretty as pretty
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.models import (MentionGroup)


class GroupsCog(BaseCog, name="Groups"):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.guild_only()
    @commands.group(name="group")
    async def group(self, ctx):
        pass

    @group.command(name="create")
    async def group_create(self, ctx):
        group = MentionGroup(guild_id=ctx.guild.id)
        await group.editor_for(ctx, "name")
        group.name = group.name.lower()

        try:
            group.save()
        except:
            raise SendableException(ctx.translate("group_already_exists"))
        else:
            group.join(ctx.author, is_owner=True)
            await ctx.send(ctx.translate("group_created").format(group=group))

    # @group.command(name = "vc")
    # @commands.has_role(_role_ids["5k+"])
    # async def group_vc(self, ctx,*, name):
    #     try:
    #         group = MentionGroup.get(name = name)
    #     except MentionGroup.DoesNotExist:
    #         raise SendableException(ctx.translate("group_not_found").format(name = name))
    #     return await self.bot.get_command("vcchannel create")(ctx, group.name)

    @group.command(name="join")
    async def group_join(self, ctx, *, name):
        try:
            group = MentionGroup.get(name=name)
        except MentionGroup.DoesNotExist:
            raise SendableException(ctx.translate("group_not_found").format(name=name))
        created = group.join(ctx.author)
        if created:
            await ctx.send(ctx.translate("group_joined").format(group=group))
        else:
            await ctx.send(ctx.translate("group_already_joined"))

    @group.command(name="leave")
    async def group_leave(self, ctx, *, name):
        try:
            group = MentionGroup.get(name=name)
        except MentionGroup.DoesNotExist:
            raise SendableException(ctx.translate("group_not_found").format(name=name))
        group.leave(ctx.author)
        await ctx.send(ctx.translate("group_left"))

    @group.command(name="mention")
    async def group_mention(self, ctx, *, name):
        try:
            group = MentionGroup.get(name=name)
        except MentionGroup.DoesNotExist:
            raise SendableException(ctx.translate("group_not_found").format(name=name))
        if group.is_member(ctx.author):
            await ctx.send(group.mention_string)
        else:
            raise SendableException(ctx.translate("group_member_only_command"))

    @group.command(name="members")
    async def group_members(self, ctx, *, name):
        try:
            group = MentionGroup.get(name=name)
        except MentionGroup.DoesNotExist:
            raise SendableException(ctx.translate("group_not_found").format(name=name))

        users = "`, `".join([str(x.user) for x in group.mention_members if x.user is not None])
        await ctx.send("`" + users + "`")

    @group.command(name="list")
    async def group_list(self, ctx):
        groups = MentionGroup.select(MentionGroup.name).where(MentionGroup.guild_id == ctx.guild.id)

        data = []
        data.append(("name",))
        for group in groups:
            data.append((group.name,))

        table = pretty.Table.from_list(data, first_header=True)
        await table.to_paginator(ctx, 10).wait()


def setup(bot):
    bot.add_cog(GroupsCog(bot))
