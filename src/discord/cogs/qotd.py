import datetime

import peewee
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
        if self.bot.production:
            self.poller.start()

    @commands.group(name = "q")
    @commands.has_guild_permissions(administrator = True)
    async def question_group(self, ctx):
        pass

    async def category_selection(self, ctx, skippable = False):
        waiter = StrWaiter(ctx, allowed_words = [x.name for x in Category], case_sensitive = False, skippable = skippable)
        try:
            category = await waiter.wait()
        except Skipped:
            return None
        else:
            return category

    @question_group.command(name = "create")
    async def question_create(self, ctx):
        question = Question()
        await question.editor_for(ctx, "value")
        question.category = await self.category_selection(ctx)
        question.save()
        await ctx.success(ctx.translate("question_created"))

    @question_group.command(name = "multi")
    async def question_multi(self, ctx):
        category = await self.category_selection(ctx)

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

    # @question_group.command(name = "lines")
    # async def question_lines(self, ctx):
    #     category = await self.category_selection(ctx)
    #     await ctx.send("Send all the questions")
    #     message = await self.bot.wait_for("message", check = lambda m : m.author.id == ctx.author.id and m.channel.id == ctx.channel.id)
    #     lines = message.content.splitlines()
    #     data = []
    #     for line in lines:
    #         data.append({"category": category, "value": line})
    #     Question.insert_many(data).execute()

    #     await ctx.success(ctx.translate("questions_created"))

    @commands.group(name = "category")
    @commands.has_guild_permissions(administrator = True)
    async def category_group(self, ctx):
        pass

    @category_group.command(name = "link")
    async def category_link(self, ctx):
        category = await self.category_selection(ctx, skippable = True)
        waiter = TextChannelWaiter(ctx, prompt = ctx.translate("category_channel_channel_prompt"))
        channel = await waiter.wait()
        category_channel, created = CategoryChannel.get_or_create(guild_id = ctx.guild.id, category = category, channel_id = channel.id)
        await ctx.success(ctx.translate("success"))

    @category_group.command(name = "create")
    async def category_create(self, ctx):
        category = Category()
        await category.editor_for(ctx, "name")
        await category.editor_for(ctx, "description")
        category.save(force_insert = True)
        await ctx.success(ctx.translate("category_created"))

    @tasks.loop(minutes = 5)
    async def poller(self):
        with database.connection_context():
            query = CategoryChannel.select()
            query = query.where( (CategoryChannel.last_day == None) | (CategoryChannel.last_day < datetime.datetime.utcnow().date()) )
            for category_channel in query:
                query = Question.select()
                query = query.where(Question.category == category_channel.category)
                query = query.join(QuestionConfig, peewee.JOIN.LEFT_OUTER)
                query = query.where( (QuestionConfig.question == None) | (QuestionConfig.asked == False) )
                query = query.order_by(peewee.fn.Rand())
                query = query.limit(1)
                question = query.first()
                if question is None:
                    continue

                question_config, created = QuestionConfig.get_or_create(question = question, category_channel = category_channel)
                question_config.asked = True
                question_config.save()
                category_channel.last_day = datetime.datetime.utcnow().date()
                category_channel.save()

                asyncio.gather(category_channel.channel.send(question.value))

def setup(bot):
    bot.add_cog(QotdCog(bot))