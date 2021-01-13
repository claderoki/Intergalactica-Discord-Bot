import datetime

import discord
from discord.ext import commands, tasks

# from src.discord.helpers.converters import EnumConverter
from src.discord.helpers.waiters import *
from src.models import Category, Question, CategoryChannel, QuestionConfig, database
import src.config as config

class QotdCog(commands.Cog, name = "Question of the day"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.group(name = "q")
    @commands.has_guild_permissions(administrator = True)
    async def question_group(self, ctx):
        pass

    @question_group.command(name = "create")
    async def question_create(self, ctx):
        question = Question()
        waiter = StrWaiter(ctx, allowed_words = [x.name for x in Category], case_sensitive = False)
        question.category = await waiter.wait()
        await question.editor_for(ctx, "value")
        question.save()
        await ctx.success(ctx.translate("question_created"))

    @question_group.command(name = "multi")
    async def question_multi(self, ctx):
        waiter = StrWaiter(ctx, allowed_words = [x.name for x in Category], case_sensitive = False)
        category = await waiter.wait()

        skipped = False
        while not skipped:
            question = Question(category = category)
            try:
                await question.editor_for(ctx, "value", on_skip = "raise", skippable = True)
            except Skipped:
                skipped = True
            else:
                question.save()
        await ctx.success(ctx.translate("questions_created"))

    @commands.group(name = "category")
    @commands.has_guild_permissions(administrator = True)
    async def category_group(self, ctx):
        pass

    @category_group.command(name = "create")
    async def category_create(self, ctx):
        category = Category()
        await category.editor_for(ctx, "name")
        await category.editor_for(ctx, "description")
        category.save(force_insert = True)
        await ctx.success(ctx.translate("category_created"))

def setup(bot):
    bot.add_cog(QotdCog(bot))