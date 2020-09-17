import datetime
import asyncio

from emoji import emojize
import discord
from discord.ext import commands, tasks

from src.discord.helpers.waiters import *
from src.models import Poll, Vote, Option
import src.config as config

db = Poll._meta.database

class PollCog(commands.Cog):


    def __init__(self, bot):
        super().__init__()
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.poll.start()

    @commands.command()
    async def results(self, ctx, poll : Poll):
        await ctx.send(embed = poll.result_embed)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not self.bot.production:
            return

        emoji = payload.emoji
        member = payload.member

        if member.bot:
            return
        with db:
            try:
                poll = Poll.get(message_id = payload.message_id, ended = False)
            except Poll.DoesNotExist:
                return

            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            allowed_reactions = {x.reaction:x for x in poll.options}

            emoji = str(emoji)
            if emoji not in allowed_reactions:
                return

            if poll.anonymous:
                await message.remove_reaction(emoji, member)

            option = allowed_reactions[emoji]

            if poll.type == "bool" or poll.type == "single":
                for _option in poll.options:
                    for vote in _option.votes.where(Vote.user_id == member.id):
                        vote.delete_instance()

                Vote.create(option = option, user_id = member)

            elif poll.type == "multi":
                Vote.get_or_create(option = option, user_id = member.id)
            



    @commands.command()
    async def selfiepoll(self, ctx, member : discord.Member):
        poll = Poll(
            question = f"Should {member} get selfie perms?",
            author_id = self.bot.user.id,
            guild_id = ctx.guild.id,
            type = "bool"
        )

        options = []
        for i, reaction in enumerate((emojize(":white_heavy_check_mark:"), emojize(":prohibited:"))):
            option = Option(value = ("Yes","No")[i], reaction = reaction)
            options.append(option)

        poll.due_date = datetime.datetime.now() + datetime.timedelta(minutes = 2)

        poll.channel = ctx.guild.get_channel(750067502352171078)

        with db:
            poll.save()

            for option in options:
                option.poll = poll
                option.save()

            message = await poll.send()
            poll.message_id = message.id

            poll.save()



    @commands.command(name = "createpoll")
    async def create_poll(self, ctx, *, question):
        poll = Poll(question = question, author_id = ctx.author.id, guild_id = ctx.guild.id)

        waiter = StrWaiter(
            ctx,
            prompt = "What type will the poll have?\n**single** = One vote per person\n**multi** = Multiple votes per person\n**bool** = Yes/No only (one vote per person)",
            allowed_words=("single", "multi", "bool"),
            case_sensitive=False)

        poll.type = await waiter.wait()

        options = []

        if poll.type == "bool":
            for i, reaction in enumerate((emojize(":white_heavy_check_mark:"), emojize(":prohibited:"))):
                option = Option(value = ("Yes","No")[i], reaction = reaction)
                options.append(option)
        else:
            waiter = IntWaiter(ctx, prompt = "How many options will the poll have? 2-4", range = range(2, 5) )

            for i in range(await waiter.wait()):
                waiter = StrWaiter(ctx, prompt = f"What will be option #{i+1}?", max_words = None)
                option = Option(value = await waiter.wait(), reaction = emojize(f":keycap_{i+1}:"))
                options.append(option)


        waiter = TimeDeltaWaiter(ctx, prompt = "When will the poll results be sent? Examples: `2 days` OR `1 hour` OR `10 weeks`", max_words = 2)
        delta = await waiter.wait()

        poll.due_date = datetime.datetime.now() + delta

        waiter = TextChannelWaiter(ctx, prompt = "What channel will the poll be sent to?")
        poll.channel_id = (await waiter.wait()).id

        with db:
            poll.save()

            for option in options:
                option.poll = poll
                option.save()

            message = await poll.send()
            poll.message_id = message.id

            poll.save()


    @tasks.loop(minutes=5)
    async def poll(self):
        with db:
            for poll in Poll.select().where(Poll.ended == False):
                if poll.due_date_passed:
                    await poll.send_results()
                    poll.ended = True
                    poll.save()




def setup(bot):
    bot.add_cog(PollCog(bot))