import asyncio

import discord
from discord.ext import commands
from emoji import emojize

from src.discord.cogs.core import BaseCog
from .wrapper import TriviaApi, QuestionType


class TriviaCog(BaseCog, name="Trivia"):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.group(name="trivia")
    @commands.guild_only()
    async def trivia(self, ctx):
        pass

    @trivia.command(name="start")
    async def trivia_start(self, ctx, amount: int = 1):
        # waiter = EnumWaiter(ctx, Category, skippable = True, reverse = True)
        # category = await waiter.wait()
        amount = min(50, max(0, amount))
        scores = {}
        i = 0
        for question in TriviaApi.get_questions(amount=amount):
            last_round = i >= amount - 1
            embed = discord.Embed(color=discord.Color.green())
            embed.title = f"Trivia, round {i + 1}/{amount}"
            description = [question.question]

            choices = {}

            if question.type == QuestionType.multiple:
                description.append("\n")
                emojis = [emojize(f":keycap_{i}:") for i in range(1, len(question.answers) + 1)]
                j = 0
                for answer in question.answers:
                    emoji = emojis[j]
                    choices[emoji] = answer.value
                    description.append(emoji + f" **{answer.value}**")
                    j += 1
            else:
                choices["✅"] = "True"
                choices["❎"] = "False"

            embed.description = "\n".join(description)
            embed.set_footer(text="Category: " + question.category.value)
            message = await ctx.send(embed=embed)

            for emoji in choices.keys():
                await message.add_reaction(emoji)

            user_answers = {}

            def check(reaction: discord.Reaction, member: discord.Member):
                if member.bot:
                    return False
                if member.guild.id != ctx.guild.id:
                    return False
                if reaction.message.id != message.id:
                    return False
                emoji = str(reaction.emoji)
                if emoji not in choices:
                    return False
                answer = question.get_answer(choices[emoji])

                if answer not in user_answers:
                    user_answers[answer] = []
                for a in question.answers:
                    if a.value == answer.value:
                        continue
                    if a in user_answers and member in user_answers[a]:
                        user_answers[a].remove(member)
                if member not in user_answers[answer]:
                    user_answers[answer].append(member)
                return False

            try:
                await ctx.bot.wait_for("reaction_add", check=check, timeout=30)
            except asyncio.TimeoutError:
                pass

            description = []
            correct_answer = None
            for answer in question.answers:
                if answer not in user_answers:
                    user_answers[answer] = []
                members = user_answers[answer]
                if answer.is_correct:
                    correct_answer = answer

                for member in members:
                    if answer.is_correct:
                        description.append(f"**{member}**")
                    if member not in scores:
                        scores[member] = int(answer.is_correct)
                    else:
                        scores[member] += int(answer.is_correct)

            embed = discord.Embed(color=discord.Color.green())
            embed.title = f"Answer: **{correct_answer.value}**"

            if len(description) > 0:
                description.insert(0, "Winners\n")

            embed.description = "\n".join(description)
            if not last_round:
                embed.set_footer(text="Next round will be starting soon...")
            await ctx.send(embed=embed)
            if not last_round:
                await asyncio.sleep(10)

            i += 1

        scores = {key: value for key, value in sorted(scores.items(), key=lambda item: item[1], reverse=True)}

        embed = discord.Embed(color=discord.Color.green())
        embed.title = "Total scores"
        description = []
        i = 0
        highest_score = 0
        for member, score in scores.items():
            if i == 0:
                highest_score = score
            star = "(🌟)" if (highest_score == score and score > 0) else ""
            description.append(f"{member}:  {score} {star}")
            i += 1
        embed.description = "\n".join(description)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TriviaCog(bot))
