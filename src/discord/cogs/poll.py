import typing
import datetime

import discord
from discord.ext import commands, tasks
from emoji import emojize
import peewee

from src.discord.helpers.waiters import *
from src.discord.helpers.pretty import prettify_dict
from src.discord.errors.base import SendableException
import src.config as config
from src.models import Change, Parameter, Poll, PollTemplate, Vote, database

class PollCog(commands.Cog, name = "Poll"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.poller.start()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not self.bot.production:
            return

        emoji = str(payload.emoji)
        member = payload.member
        if member.bot:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if not message.author.bot:
            return

        with database.connection_context():
            try:
                poll = Poll.get(message_id = payload.message_id, ended = False)
            except Poll.DoesNotExist:
                return

            allowed_reactions = {x.reaction:x for x in poll.options}

            if emoji not in allowed_reactions:
                return

            if poll.anonymous:
                await message.remove_reaction(emoji, member)

            option = allowed_reactions[emoji]

            user_votes = [list(x.votes.where(Vote.user_id == member.id)) for x in poll.options]

            if len(user_votes) == poll.max_votes_per_user:
                first_vote = user_votes[0]
                first_vote.delete_instance()

            if poll.role_id_needed_to_vote is not None:
                role = member.guild.get_role(poll.role_id_needed_to_vote)

                if role not in member.roles:
                    #TODO: translate!
                    return await member.send(f"To vote for this poll you need the **{role}** role.")

            vote, created = Vote.get_or_create(option = option, user_id = member.id)

            if created:
                pass

    async def setup_poll(self, ctx, poll):
        prompt = lambda x : ctx.translate(f"poll_{x}_prompt")
        cls = poll.__class__
        is_template = isinstance(poll, PollTemplate)

        if poll.type is None or is_template:
            waiter = EnumWaiter(ctx, Poll.Type, prompt = prompt("type"), skippable = cls.type.null)
            try:
                poll.type = await waiter.wait()
            except Skipped: pass

        if poll.channel_id is None or is_template:
            waiter = TextChannelWaiter(ctx, prompt = prompt("channel_id"), skippable = cls.channel_id.null)
            try:
                poll.channel_id = (await waiter.wait()).id
            except Skipped: pass

        if poll.result_channel_id is None or is_template:
            waiter = TextChannelWaiter(ctx, prompt = prompt("result_channel_id"), skippable = cls.result_channel_id.null)
            try:
                poll.result_channel_id = (await waiter.wait()).id
            except Skipped: pass

        if poll.anonymous is None or is_template:
            waiter = BoolWaiter(ctx, prompt = prompt("anonymous"), skippable = cls.anonymous.null)
            try:
                poll.anonymous = await waiter.wait()
            except Skipped: pass

        if poll.type == Poll.Type.bool:
            poll.max_votes_per_user = 1
        elif poll.max_votes_per_user is None or is_template:
            waiter = IntWaiter(ctx, prompt = prompt("max_votes_per_user"), skippable = cls.max_votes_per_user.null)
            try:
                poll.max_votes_per_user = await waiter.wait()
            except Skipped: pass

        if poll.role_id_needed_to_vote is None or is_template:
            waiter = RoleWaiter(ctx, prompt = prompt("role_id_needed_to_vote"), skippable = cls.role_id_needed_to_vote.null)
            try:
                poll.role_id_needed_to_vote = (await waiter.wait()).id
            except Skipped: pass

        if (poll.vote_percentage_to_pass is None or is_template) and poll.type == Poll.Type.bool:
            waiter = IntWaiter(ctx, range = range(0,101), prompt = prompt("vote_percentage_to_pass"), skippable = cls.vote_percentage_to_pass.null)
            try:
                poll.vote_percentage_to_pass = await waiter.wait()
            except Skipped: pass

        if poll.pin is None or is_template:
            waiter = BoolWaiter(ctx, prompt = prompt("pin"), skippable = cls.pin.null)
            try:
                poll.pin = await waiter.wait()
            except Skipped: pass

        if poll.delete_after_results is None or is_template:
            waiter = BoolWaiter(ctx, prompt = prompt("delete_after_results"), skippable = cls.delete_after_results.null)
            try:
                poll.delete_after_results = await waiter.wait()
            except Skipped: pass

        if poll.role_id_needed_to_vote is not None and (poll.delete is None or is_template):
            waiter = BoolWaiter(ctx, prompt = prompt("mention_role"), skippable = cls.mention_role.null)
            try:
                poll.mention_role = await waiter.wait()
            except Skipped: pass

        return poll

    @commands.group(name = "poll")
    async def poll_group(self, ctx):
        if ctx.guild.id in (695416318681415790, 761624318291476482):
            pass
        else:
            if not ctx.author.guild_permissions.administrator:
                raise commands.errors.MissingPermissions(["administrator"])

    @poll_group.command()
    async def template(self, ctx, name):
        prompt = lambda x : ctx.translate(f"poll_{x}_prompt")

        template, _ = PollTemplate.get_or_create(name = name, guild_id = ctx.guild.id)
        poll = await self.setup_poll(ctx, template)

        waiter = TimeDeltaWaiter(ctx, prompt = prompt("due_date"), max_words = 2)
        message = await waiter.wait(raw = True)
        poll.delta = message.content

        poll.save()

        asyncio.gather(ctx.send("OK"))

    @poll_group.command(name = "templateview")
    async def template_view(self, ctx, name):
        try:
            template = PollTemplate.get(name = name, guild_id = ctx.guild.id)
        except PollTemplate.DoesNotExist:
            raise SendableException(ctx.translate("poll_template_does_not_exist"))

        columns = template.shared_columns
        del columns["guild_id"]

        if columns["result_channel_id"] is not None:
            columns["result_channel"] = str(ctx.guild.get_channel(columns["result_channel_id"]))
            del columns["result_channel_id"]
        if columns["channel_id"] is not None:
            columns["channel"] = str(template.channel)
            del columns["channel_id"]
        if columns["role_id_needed_to_vote"] is not None:
            columns["role_needed_to_vote"] = str(ctx.guild.get_role(template.role_id_needed_to_vote))
            del columns["role_id_needed_to_vote"]

        new_columns = {}
        for key, value in columns.items():
            new_key = key.replace("_", " ").capitalize()
            if isinstance(value, bool):
                new_key += "?"
            new_columns[new_key] = value

        lines = prettify_dict(new_columns)

        embed = discord.Embed(
            color       = ctx.guild_color,
            title       = f"Config of poll-template '{name}'",
            description = f"```\n{lines}```"
        )
        return asyncio.gather(ctx.send(embed = embed))



    @poll_group.command(name = "create")
    async def create_poll(self, ctx, template_name):
        prompt = lambda x : ctx.translate(f"poll_{x}_prompt")

        template       = PollTemplate.get(name = template_name, guild_id = ctx.guild.id)

        poll           = Poll.from_template(template)
        poll.author_id = ctx.author.id

        waiter = StrWaiter(ctx, prompt = prompt("question"), max_words = None)
        poll.question = await waiter.wait()

        await self.setup_poll(ctx, poll)

        if poll.type == Poll.Type.custom:
            options = []
            option_range = range(2, 5)
            waiter = IntWaiter(ctx, range = option_range, prompt = ctx.translate("option_count_prompt") )
            for i in range(await waiter.wait()):
                waiter = StrWaiter(ctx, max_words = None, prompt = ctx.translate("option_value_prompt").format(index = i+1))
                options.append(await waiter.wait())

        if poll.due_date is None:
            waiter = TimeDeltaWaiter(ctx, prompt = prompt("due_date"), max_words = 2)
            delta = await waiter.wait()
            poll.due_date = datetime.datetime.utcnow() + delta

        poll.save()

        if poll.type == Poll.Type.bool:
            poll.create_bool_options()
        else:
            poll.create_options(options)

        message = await poll.send()
        poll.message_id = message.id

        poll.save()


    @poll_group.group(name = "change")
    async def change(self, ctx):
        pass

    @change.command("delete")
    async def change_delete(self, ctx, discordObject : typing.Union[discord.TextChannel, discord.Role] ):
        poll_channel = ctx.channel

        template       = PollTemplate.get(name = "change", guild_id = ctx.guild.id)
        poll           = Poll.from_template(template)
        poll.author_id = ctx.author.id
        poll.type      = Poll.Type.bool
        poll.save()

        poll.create_bool_options()

        change = Change.create(poll = poll, action = "delete", type = Change.Type[discordObject.__class__.__name__.lower()])
        Parameter.create(change = change, key = "id",   value = discordObject.id)

        poll.question = poll.generate_question()

        message = await poll.send()
        poll.message_id = message.id
        poll.save()

    @change.command("create")
    async def change_create(self, ctx, type : str,  name : str):
        template       = PollTemplate.get(name = "change", guild_id = ctx.guild.id)
        poll           = Poll.from_template(template)
        poll.author_id = ctx.author.id
        poll.type      = Poll.Type.bool
        poll.save()

        poll.create_bool_options()

        await self.setup_poll(ctx, poll)
        change = Change.create(action = "create", poll = poll, type = Change.Type[type.lower()])
        change.create_param("name", name)

        poll.question = poll.generate_question()

        message = await poll.send()
        poll.message_id = message.id
        poll.save()

    @tasks.loop(minutes=2)
    async def poller(self):
        with database:
            for poll in Poll.select().where(Poll.ended == False):
                if poll.due_date_passed:

                    if poll.type == Poll.Type.bool and poll.passed:
                        for change in poll.changes:
                            await change.implement()
                            change.implemented = True
                            change.save()

                    await poll.send_results()
                    poll.ended = True
                    if poll.delete_after_results:
                        message = await poll.channel.fetch_message(poll.message_id)
                        asyncio.gather(message.delete())

                    poll.save()


def setup(bot):
    bot.add_cog(PollCog(bot))