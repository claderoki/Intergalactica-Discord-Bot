import asyncio

import discord
from discord.ext import commands

import src.config as config
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.cogs.custom.shared.helpers import GuildHelper
from src.discord.helpers.waiters import *

class Admin(BaseCog):
    bronk_id = 771781840012705792

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guilds = [x for x in self.bot.guilds if x.owner_id == self.bronk_id]

    async def update_bot(self, ctx):
        await ctx.success("Updating the bot...")
        import git
        repo = git.Repo(config.path)
        repo.remotes.origin.pull()

    async def restart_bot(self, ctx):
        ctx.bot.restarting = True
        await ctx.success("Restarting the bot...")
        await ctx.bot.logout()

    @commands.is_owner()
    @commands.command()
    async def update(self, ctx):
        await self.update_bot(ctx)
        await self.restart_bot(ctx)

    @commands.is_owner()
    @commands.command()
    async def restart(self, ctx):
        await self.restart_bot(ctx)

    @commands.command(name="unusedroles")
    async def unused_roles(self, ctx):
        roles = []
        for role in ctx.guild.roles:
            if len(role.members) == 0:
                roles.append(role)
        lines = ["```\n"]
        for role in roles:
            lines.append(role.name)
        lines.append("```")
        asyncio.gather(ctx.send("\n".join(lines)))

    @commands.is_owner()
    @commands.group()
    async def tester(self, ctx):
        pass

    @tester.command(name="add", aliases=["=", "+"])
    async def add_tester(self, ctx, member: discord.Member):
        human = ctx.get_human(user=member)
        human.tester = True
        human.save()
        asyncio.gather(ctx.success())

    @tester.command(name="remove", aliases=["-", "del"])
    async def remove_tester(self, ctx, member: discord.Member):
        human = ctx.get_human(user=member)
        human.tester = False
        human.save()
        asyncio.gather(ctx.success())

    @commands.group()
    @commands.is_owner()
    async def emoji(self, ctx):
        pass

    @commands.command()
    @commands.is_owner()
    async def invo(self, ctx):
        guild = ctx.bot.get_guild(761624318291476482)
        invite_url = await GuildHelper.get_invite_url(guild)
        await ctx.send(invite_url)

    @commands.command()
    @commands.is_owner()
    async def leave(self, ctx, guild_id: int):
        guild = ctx.bot.get_guild(guild_id)

        waiter = BoolWaiter(ctx, prompt=f"Are you sure you want me to leave '{guild}'?")
        if not await waiter.wait():
            return await ctx.send("Fine. I'll stay a little longer.")

        await guild.leave()
        await ctx.send("OK")

    # @emoji.command(name="add")
    # async def emoji_add(self, ctx, *, name: lambda x: x.lower().replace(" ", "_")):
    #     if len(ctx.message.attachments) == 0:
    #         raise SendableException(ctx.translate("no_attachments"))
    #     image = ctx.message.attachments[0]

    #     available_guilds = [x for x in self.guilds if len(x.emojis) < x.emoji_limit]
    #     guild = available_guilds[0]
    #     emoji = await guild.create_custom_emoji(name=name, image=await image.read())
    #     SavedEmoji.create(name=emoji.name, guild_id=guild.id, emoji_id=emoji.id)
    #     asyncio.gather(ctx.send(ctx.translate("emoji_created")))

    # @emoji.command(name="remove")
    # async def emoji_remove(self, ctx, *, name: lambda x: x.lower().replace(" ", "_")):
    #     try:
    #         emoji = SavedEmoji.get(name=name)
    #     except SavedEmoji.DoesNotExist:
    #         return
    #     emoji.delete_instance()

    #     asyncio.gather(ctx.send(ctx.translate("emoji_removed")))


async def setup(bot):
    await bot.add_cog(Admin(bot))
