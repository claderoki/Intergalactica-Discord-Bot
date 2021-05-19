import asyncio
import datetime
import random

import discord
from discord.ext import commands, tasks

from src.wrappers.zalgo import Zalgo
import src.config as config
from src.models import Human, Prankster, NicknamePrank, HumanItem, Item, EmojiPrank, RolePrank, database
from src.discord.errors.base import SendableException
import src.discord.helpers.pretty as pretty
from src.discord.helpers.waiters import StrWaiter, BoolWaiter
from src.discord.cogs.core import BaseCog

pranks_in_progress = []

class Prank(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.prank_poller, check = self.bot.production)

    def get_random_words(self, zalgo = True, nick = True):
        generator = self.bot.get_random_reddit_words(
            nsfw       = False,
            max_words  = 10,
            max_length = 5
        )
        if zalgo:
            words = [Zalgo().zalgofy(x) for x in generator]
        else:
            words = list(generator)

        possible_combinations = []
        if nick:
            max_length = 32
        else:
            max_length = 100
        current_combination = None
        for word1 in words:
            if current_combination is not None:
                if current_combination not in possible_combinations:
                    possible_combinations.append(current_combination)

            current_combination = []
            if len(word1) <= max_length:
                current_combination.append(word1)
            for word2 in words:
                if word1 != word2:
                    if sum([len(x) for x in current_combination])+len(word2) <= max_length:
                        current_combination.append(word2)

        return random.choice(possible_combinations)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not self.bot.production:
            return

        prankstee, _ = Prankster.get_or_create(user_id = message.author.id, guild_id = message.guild.id)
        if not prankstee.pranked:
            return
        if prankstee.prank_type != Prankster.PrankType.emoji:
            return
        prank = prankstee.current_prank
        asyncio.gather(message.add_reaction(prank.emoji), return_exceptions = False)

    @commands.command()
    async def zalgo(self, ctx):
        await ctx.send(" ".join(self.get_random_words(nick = False)))

    @commands.group()

    @commands.guild_only()
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def prank(self, ctx):
        pass

    @prank.command(name = "toggle", aliases = ["enable", "disable"])
    async def prank_toggle(self, ctx):
        prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)
        if prankster.enabled and prankster.days_ago_last_pranked == 0:
            raise SendableException(ctx.translate("pranked_too_recently"))

        values = {"enable": True, "disable": False, "toggle": not prankster.enabled}
        prankster.enabled = values[ctx.invoked_with]
        prankster.last_pranked = None
        prankster.save()
        asyncio.gather(ctx.send(f"Okay. Pranking is now " + ("on" if prankster.enabled else "off")))

    @prank.command(name = "list")
    async def prank_list(self, ctx):
        query = Prankster.select(Prankster.user_id, Prankster.guild_id, Prankster.pranked)
        query = query.where(Prankster.guild_id == ctx.guild.id)
        query = query.where(Prankster.enabled == True)
        query = query.order_by(Prankster.pranked.desc())

        table = pretty.Table()
        table.add_row(pretty.Row(("Prankster", "Pranked?"), header = True))

        for prankster in query:
            member = prankster.member
            if member is not None:
                table.add_row(pretty.Row((str(member), pretty.prettify_value(prankster.pranked))))
        await table.to_paginator(ctx, 15).wait()

    @prank.command(name = "scoreboard")
    async def prank_scoreboard(self, ctx):

        query = """SELECT
prankster.user_id, COUNT(nickname_prank.id) as people_nick_pranked
FROM
prankster
INNER JOIN nickname_prank ON prankster.id = nickname_prank.pranked_by_id
WHERE prankster.guild_id = {guild_id}
GROUP BY user_id
ORDER BY people_nick_pranked DESC"""

        table = pretty.Table()
        table.add_row(pretty.Row(("Prankster", "Pranks (nick)"), header = True))

        cursor = database.execute_sql(query.format(guild_id = ctx.guild.id))
        for user_id, people_nick_pranked in cursor:
            member = ctx.guild.get_member(user_id)
            if member is None:
                continue

            table.add_row(pretty.Row((str(member), people_nick_pranked)))

        await table.to_paginator(ctx, 15).wait()

    @prank.command(name = "stats")
    async def prank_stats(self, ctx, member : discord.Member = None):
        member = member or ctx.author

        prankster, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)

        embed = discord.Embed(color = ctx.guild_color)
        query = NicknamePrank.select()
        distinct_query = NicknamePrank.select(NicknamePrank.victim)

        wheres = []
        wheres.append(NicknamePrank.pranked_by == prankster)

        for where in wheres:
            query = query.where(where)
            distinct_query = distinct_query.where(where)

        lines = []
        lines.append(f"Total people pranked: {query.count()}")
        lines.append(f"Unique people pranked: {distinct_query.distinct(True).count()}")
        victim_query = NicknamePrank.select().where(NicknamePrank.victim == prankster).where(NicknamePrank.finished == True)
        lines.append(f"Total times been pranked: {victim_query.count()}")

        embed.add_field(name = f"Nickname Pranks", value = "\n".join(lines), inline = False)

        asyncio.gather(ctx.send(embed = embed))

    async def prank_check(self, ctx, member, name = "human"):
        if member.bot:
            raise SendableException(ctx.translate("cannot_prank_bot"))
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_prank_self"))

        ctx.prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)
        if not ctx.prankster.enabled:
            raise SendableException(ctx.translate("prankster_pranking_disabled"))

        ctx.victim, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
        if not ctx.victim.enabled:
            raise SendableException(ctx.translate("victim_pranking_disabled"))
        if ctx.victim.pranked:
            raise SendableException(ctx.translate("already_pranked"))

        if ctx.command.name == "nickname":
            cls = NicknamePrank
        elif ctx.command.name == "emoji":
            cls = EmojiPrank
        elif ctx.command.name == "role":
            cls = RolePrank
        else:
            cls = None
        ctx.prank_class = cls
        ctx.human = ctx.get_human()
        ctx.has_item = False
        if cls.item_code is not None:
            ctx.human_item = HumanItem.get_or_none(
                human = ctx.human,
                item = Item.get(Item.code == cls.item_code)
            )
            ctx.has_item = ctx.human_item is not None and ctx.human_item.amount > 0

        ctx.cost = cls.cost

        if not ctx.has_item:
            ctx.raise_if_not_enough_gold(ctx.cost, ctx.human)
            waiter = BoolWaiter(ctx, prompt = ctx.translate("gold_verification_check").format(gold = ctx.cost))
            if not await waiter.wait():
                raise SendableException(ctx.translate("canceled"))

    async def create_prank(self, ctx, embed_description = None, **kwargs):
        ctx.prankster.last_pranked = datetime.datetime.utcnow()
        ctx.victim.pranked = True
        ctx.victim.prank_type = ctx.prank_class.prank_type

        prank = ctx.prank_class(
            start_date = datetime.datetime.utcnow(),
            end_date = datetime.datetime.utcnow() + ctx.prank_class.duration,
            victim = ctx.victim,
            pranked_by = ctx.prankster,
            **kwargs,
        )
        if ctx.has_item:
            prank.purchase_type = prank.PurchaseType.item
            ctx.human_item.amount -= 1
            ctx.human_item.save()
        else:
            prank.purchase_type = prank.PurchaseType.gold
            ctx.human.gold -= ctx.cost
            ctx.human.save()

        prank.save()
        ctx.victim.save()
        ctx.prankster.save()

        await prank.apply()

        embed = self.bot.get_base_embed()
        embed.description = embed_description
        embed.timestamp = prank.end_date
        if ctx.has_item:
            embed.set_footer(text = f"-{ctx.human_item.item.name}\nWill stay into effect until")
        else:
            embed.set_footer(text = f"-{ctx.cost}\nWill stay into effect until")

        await ctx.send(embed = embed)

    async def pre_prank(self, ctx, member):
        if member.id in pranks_in_progress:
            raise SendableException(ctx.translate("already_in_progress"))
        pranks_in_progress.append(member.id)
        ctx.member = member

    @prank.command(name = "nickname", aliases = ["nick"] )
    async def prank_nickname(self, ctx, member : discord.Member):
        await self.pre_prank(ctx, member)
        if not self.bot.can_change_nick(ctx.member):
            raise SendableException(ctx.translate("cannot_change_nickname"))
        if not self.bot.can_change_nick(ctx.author):
            raise SendableException(ctx.translate("cannot_toggle_because_cannot_change_nickname"))

        await self.prank_check(ctx, ctx.member)

        waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("nickname_prank_prompt"), max_length = 32)
        new_nickname = await waiter.wait()
        if new_nickname is None:
            raise SendableException(ctx.translate("timed_out"))

        await self.create_prank(
            ctx,
            embed_description = f"Nickname of {ctx.member.mention} has been changed to **{new_nickname}**.",
            new_nickname = new_nickname,
            old_nickname = ctx.member.nick
        )

    @prank.command(name = "role")
    async def prank_role(self, ctx, member : discord.Member):
        await self.pre_prank(ctx, member)

        await self.prank_check(ctx, ctx.member)

        waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("role_prank_prompt"))
        role_name = await waiter.wait()

        await self.create_prank(
            ctx,
            embed_description = None,
            role_name = role_name
        )

    @prank.command(name = "emoji")
    async def prank_emoji(self, ctx, member : discord.Member):
        await self.pre_prank(ctx, member)
        await self.prank_check(ctx, ctx.member)

        waiter = StrWaiter(ctx, max_words = 1, prompt = ctx.translate("emoji_prank_prompt"))
        emoji_ = await waiter.wait()
        try:
            await ctx.message.add_reaction(emoji_)
        except:
            raise SendableException("Could not use emoji")

        await self.create_prank(
            ctx,
            embed_description = None,
            emoji = emoji_
        )

    @prank_emoji.after_invoke
    @prank_nickname.after_invoke
    @prank_role.after_invoke
    async def after_prank(self, ctx):
        try:
            pranks_in_progress.remove(ctx.member.id)
        except:
            pass

    @commands.guild_only()
    @commands.has_guild_permissions(administrator = True)
    @prank.command(name = "revert")
    async def prank_revert(self, ctx, member : discord.Member):
        """
        3 types:
            1. Admin revert (when admin wants to revert a prank and give the pranker their gold back)
            2. Member reverts their own prank by spending gold (1k?)
            3. Someone who pranked someone reverts their prank on them
        """

        prankster, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
        prank = prankster.current_prank
        if prank is not None:
            prank.end_date = prank.start_date
            prank.save()

            human = ctx.get_human(user = prank.pranked_by.user_id)
            if prank.purchase_type == NicknamePrank.PurchaseType.gold:
                human.gold += prank.cost
                human.save()
            elif prank.purchase_type == NicknamePrank.PurchaseType.item:
                human.add_item(Item.get(code = prank.item_code), 1)
            await ctx.success(ctx.translate("prank_reverted"))

    @tasks.loop(minutes = 1)
    async def prank_poller(self):
        with database.connection_context():
            pranks = [NicknamePrank, RolePrank, EmojiPrank]

            for cls in pranks:
                query = cls.select()
                query = query.where(cls.finished == False)
                if cls != NicknamePrank:
                    query = query.where(cls.end_date <= datetime.datetime.utcnow())
                for prank in query:
                    if cls != NicknamePrank or prank.end_date_passed:
                        prank.finished = True
                        prank.victim.pranked = False
                        prank.victim.prank_type = None
                        prank.save()
                        prank.victim.save()
                        if prank.victim.member:
                            asyncio.gather(prank.revert())
                    else:
                        if prank.should_reapply:
                            asyncio.gather(prank.apply())

def setup(bot):
    bot.add_cog(Prank(bot))