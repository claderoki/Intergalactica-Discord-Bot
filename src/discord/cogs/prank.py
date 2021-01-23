import asyncio
import datetime

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Human, Prankster, NicknamePrank, HumanItem, Item, database
from src.discord.errors.base import SendableException
import src.discord.helpers.pretty as pretty
from src.discord.helpers.waiters import StrWaiter, BoolWaiter

class Prank(discord.ext.commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.prank_poller.start()

    @commands.group()
    @commands.guild_only()
    async def prank(self, ctx):
        pass

    @prank.command(name = "toggle")
    async def prank_toggle(self, ctx):
        if not self.bot.can_change_nick(ctx.author):
            raise SendableException(ctx.translate("cannot_toggle_because_cannot_change_nickname"))

        prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)

        if prankster.enabled and prankster.days_ago_last_pranked == 0:
            raise SendableException(ctx.translate("pranked_too_recently"))

        prankster.enabled = not prankster.enabled
        prankster.last_pranked = None
        prankster.save()
        asyncio.gather(ctx.send(f"Okay. Pranking is now " + ("on" if prankster.enabled else "off")))

    @prank.command(name = "list")
    async def prank_list(self, ctx):
        query = Prankster.select()
        query = query.where(Prankster.guild_id == ctx.guild.id)
        query = query.where(Prankster.enabled == True)
        query = query.order_by(Prankster.pranked.desc())

        table = pretty.Table()
        table.add_row(pretty.Row(("Prankster", "Pranked?"), header = True))

        for prankster in query:
            member = prankster.member
            if member is not None:
                table.add_row(pretty.Row((str(member), pretty.prettify_value(prankster.pranked))))
        await table.to_paginator(ctx, 10).wait()

    @prank.command(name = "nickname", aliases = ["nick"] )
    async def prank_nickname(self, ctx, member : discord.Member):
        if member.bot:
            raise SendableException(ctx.translate("cannot_prank_bot"))
        if not self.bot.can_change_nick(member):
            raise SendableException(ctx.translate("cannot_change_nickname"))

        prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)
        if not prankster.enabled:
            raise SendableException(ctx.translate("prankster_pranking_disabled"))

        victim, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
        if not victim.enabled:
            raise SendableException(ctx.translate("victim_pranking_disabled"))
        if victim.pranked:
            raise SendableException(ctx.translate("already_pranked"))

        human, _ = Human.get_or_create(user_id = ctx.author.id)
        human_item = HumanItem.get_or_none(
            human = human,
            item = Item.get(Item.code == "jester_hat")
        )
        has_hat = human_item is not None and human_item.amount > 0

        if not has_hat:
            cost = 500
            ctx.raise_if_not_enough_gold(cost, human)
            waiter = BoolWaiter(ctx, prompt = ctx.translate("gold_verification_check").format(gold = cost))
            if not await waiter.wait():
                return asyncio.gather(ctx.send(ctx.translate("canceled")))

        waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("nickname_prank_prompt"), max_length = 32)
        new_nickname = await waiter.wait()

        prankster.last_pranked = datetime.datetime.utcnow()
        victim.pranked = True
        victim.prank_type = Prankster.PrankType.nickname

        prank = NicknamePrank(
            new_nickname = new_nickname,
            old_nickname = member.nick,
            start_date = datetime.datetime.utcnow(),
            end_date = datetime.datetime.utcnow() + datetime.timedelta(days = 1),
            victim = victim,
            pranked_by = prankster
        )
        if has_hat:
            human_item.amount -= 1
            human_item.save()
        else:
            human.gold -= cost
            human.save()
        prank.save()
        victim.save()
        prankster.save()

        await prank.apply()

        embed = self.bot.get_base_embed()
        embed.description = f"Nickname of {member.mention} has been changed to **{new_nickname}**."
        embed.timestamp = prank.end_date
        if has_hat:
            embed.set_footer(text = f"-{human_item.item.name}\nWill stay into effect until")
        else:
            embed.set_footer(text = f"-{cost}\nWill stay into effect until")

        asyncio.gather(ctx.send(embed = embed))

    # @prank.command(name = "role")
    # async def prank_role(self, ctx, member : discord.Member):
    #     if member.bot:
    #         raise SendableException(ctx.translate("cannot_prank_bot"))
    #     if not self.bot.can_change_nick(member):
    #         raise SendableException(ctx.translate("cannot_change_nickname"))

    #     prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)
    #     if not prankster.enabled:
    #         raise SendableException(ctx.translate("prankster_pranking_disabled"))

    #     victim, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
    #     if not victim.enabled:
    #         raise SendableException(ctx.translate("victim_pranking_disabled"))
    #     if victim.pranked:
    #         raise SendableException(ctx.translate("already_pranked"))

    #     cost = 500
    #     ctx.raise_if_not_enough_gold(cost, human)
    #     waiter = BoolWaiter(ctx, prompt = ctx.translate("gold_verification_check").format(gold = cost))
    #     if not await waiter.wait():
    #         return asyncio.gather(ctx.send(ctx.translate("canceled")))

    #     waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("role_prank_prompt"), max_length = 32)
    #     role_name = await waiter.wait()

    #     prankster.last_pranked = datetime.datetime.utcnow()
    #     victim.pranked = True
    #     victim.prank_type = Prankster.PrankType.role

    #     prank = RolePrank(
    #         role_name = role_name,
    #         start_date = datetime.datetime.utcnow(),
    #         end_date = datetime.datetime.utcnow() + datetime.timedelta(days = 1),
    #         victim = victim,
    #         pranked_by = prankster
    #     )

    #     human.gold -= cost
    #     human.save()
    #     prank.save()
    #     victim.save()
    #     prankster.save()

    #     await prank.apply()

    #     embed = self.bot.get_base_embed()
    #     embed.description = f"OK"
    #     embed.timestamp = prank.end_date
    #     embed.set_footer(text = f"-{cost}\nWill stay into effect until")
    #     asyncio.gather(ctx.send(embed = embed))

    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    @prank.command(name = "revert")
    async def prank_revert(self, ctx, member : discord.Member = None):
        """
        3 types:
            1. Admin revert (when admin wants to revert a prank and give the pranker their gold back)
            2. Member reverts their own prank by spending gold (1k?)
            3. Someone who pranked someone reverts their prank on them 
        """

        prankster, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
        if prankster.pranked:
            prank = NicknamePrank.select().where(NicknamePrank.victim == prankster).where(NicknamePrank.finished == False).first()
            prank.end_date = datetime.datetime.utcnow()
            prank.save()

            human, _ = Human.get_or_create(user_id = prank.pranked_by.user_id)
            human.gold += 500
            human.save()
            await ctx.success(ctx.translate("prank_reverted"))

    @tasks.loop(minutes = 1)
    async def prank_poller(self):
        with database.connection_context():
            query = NicknamePrank.select()
            query = query.where(NicknamePrank.finished == False)

            for prank in query:
                if prank.end_date_passed:
                    prank.finished = True
                    prank.victim.pranked = False
                    prank.victim.prank_type = None
                    prank.save()
                    prank.victim.save()
                    if prank.victim.member:
                        asyncio.gather(prank.revert())
                else:
                    if prank.victim.member and prank.victim.member.display_name != prank.new_nickname:
                        asyncio.gather(prank.apply())

def setup(bot):
    bot.add_cog(Prank(bot))