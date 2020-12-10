import asyncio
import datetime

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Human, Prankster, NicknamePrank, database
from src.discord.errors.base import SendableException
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
    async def prank(self, ctx):
        pass

    @prank.command(name = "toggle")
    async def prank_toggle(self, ctx):
        prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)

        if prankster.enabled and prankster.days_ago_last_pranked == 0:
            raise SendableException(ctx.translate("pranked_too_recently"))

        prankster.enabled = not prankster.enabled
        prankster.last_pranked = None
        prankster.save()
        asyncio.gather(ctx.send(ctx.translate("saved")))

    @prank.command(name = "list")
    async def prank_list(self, ctx):
        lines = []
        for prankster in Prankster.select().where(Prankster.guild_id == ctx.guild.id).where(Prankster.enabled == True):
            lines.append(str(prankster.member))

        lines = "\n".join(lines)
        asyncio.gather(ctx.send(f"```\n{lines}```"))

    @commands.guild_only()
    @prank.command(name = "nickname", aliases = ["nick"] )
    async def prank_nickname(self, ctx, member : discord.Member):
        if member.bot:
            raise SendableException(ctx.translate("cannot_prank_bot"))

        if ctx.guild.me.top_role.position <= member.top_role.position or member.id == ctx.guild.owner_id:
            raise SendableException(ctx.translate("cannot_change_nickname"))

        prankster, _ = Prankster.get_or_create(user_id = ctx.author.id, guild_id = ctx.guild.id)
        if not prankster.enabled:
            raise SendableException(ctx.translate("pranking_disabled"))

        prankstee, _ = Prankster.get_or_create(user_id = member.id, guild_id = ctx.guild.id)
        if not prankstee.enabled:
            raise SendableException(ctx.translate("pranking_disabled"))
        if prankstee.pranked:
            raise SendableException(ctx.translate("already_pranked"))

        human, _ = Human.get_or_create(user_id = ctx.author.id)
        cost = 500
        raise_if_not_enough_gold(ctx, cost, human)

        waiter = BoolWaiter(ctx, prompt = ctx.translate("gold_verification_check").format(gold = cost))
        if not await waiter.wait():
            return asyncio.gather(ctx.send(ctx.translate("canceled")))

        waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("nickname_prank_prompt"), max_length = 32)
        new_nickname = await waiter.wait()

        prankster.last_pranked = datetime.datetime.utcnow()
        prankstee.pranked = True
        prankstee.prank_type = Prankster.PrankType.nickname

        prank = NicknamePrank(
            new_nickname = new_nickname,
            old_nickname = member.display_name,
            start_date = datetime.datetime.utcnow(),
            end_date = datetime.datetime.utcnow() + datetime.timedelta(days = 1),
            victim = prankstee,
            pranked_by = prankster
        )

        human.gold -= cost
        human.save()
        prank.save()
        prankstee.save()
        prankster.save()

        await prank.apply()

        embed = self.bot.get_base_embed()
        embed.description = f"Nickname of {member.mention} has been changed to **{new_nickname}**."
        embed.timestamp = prank.end_date
        embed.set_footer(text = f"-{cost}\nWill stay into effect until")

        asyncio.gather(ctx.send(embed = embed))

    @tasks.loop(minutes = 1)
    async def prank_poller(self):
        with database.connection_context():
            for prank in NicknamePrank.select().where(NicknamePrank.finished == False):
                if prank.end_date_passed:
                    prank.finished = True
                    prank.victim.pranked = False
                    prank.victim.prank_type = None
                    prank.save()
                    prank.victim.save()
                    asyncio.gather(prank.revert())
                else:
                    if prank.victim.member.display_name != prank.new_nickname:
                        asyncio.gather(prank.apply())

def raise_if_not_enough_gold(ctx, gold, human, name = "you"):
    if human.gold < gold:
        raise SendableException(ctx.translate(f"{name}_not_enough_gold"))

def setup(bot):
    bot.add_cog(Prank(bot))