import random
import asyncio

import discord
from discord.ext import commands, tasks
from countryinfo import CountryInfo
import peewee

import src.config as config
from src.models import HumanItem, Human, Fight, Reminder, Pigeon, Buff, PigeonBuff, PigeonRelationship, Earthling, Item, Exploration, LanguageMastery, Mail, Settings, SystemMessage, Date, database
from src.models.base import PercentageField
from src.discord.helpers.waiters import *
from src.utils.country import Country
from src.discord.errors.base import SendableException
from src.discord.helpers.pretty import prettify_dict, limit_str, Table, Row
from src.discord.helpers.exploration_retrieval import ExplorationRetrieval, MailRetrieval
from src.utils.enums import Gender
from src.discord.helpers.converters import EnumConverter
from src.discord.cogs.core import BaseCog

class ItemWaiter(StrWaiter):
    def __init__(self, ctx, in_inventory = True, **kwargs):
        super().__init__(ctx, max_words = None, **kwargs)
        self.show_instructions = False
        self.case_sensitive = False

        if in_inventory:
            query = HumanItem.select()
            query = query.where(HumanItem.human == ctx.get_human())
            query = query.where(HumanItem.amount > 0)
            self.inventory = list(query)
            self.items = [x.item for x in self.inventory]
        else:
            self.items = list(Item.select())

        self.allowed_words = [x.name.lower() for x in self.items]

    async def wait(self, *args, **kwargs):
        data = [(x.item.name, x.amount) for x in self.inventory]
        data.insert(0, ("name", "amount"))
        table = Table.from_list(data, first_header = True)
        asyncio.gather(table.to_paginator(self.ctx, 15).wait())
        await asyncio.sleep(0.5)
        return await super().wait(*args, **kwargs)

    def convert(self, argument):
        for item in self.items:
            if item.name.lower() == argument.lower():
                return item
        raise ConversionFailed("Item not found.")

class PigeonCog(BaseCog, name = "Pigeon"):
    subcommands_no_require_pigeon = ["buy", "history", "scoreboard", "help", "inbox", "pigeon"]
    subcommands_no_require_available = ["status", "relationships", "reject", "stats", "languages", "retrieve", "gender", "name", "accept"] + subcommands_no_require_pigeon
    subcommands_no_require_stats = ["heal", "clean", "feed", "play", "date", "poop"] + subcommands_no_require_available

    def __init__(self, bot):
        super().__init__(bot)
        self.message_counts = {}

    def get_base_embed(self, guild):
        embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed

    def get_pigeon_channel(self, guild):
        with database.connection_context():
            settings, _ = Settings.get_or_create(guild_id = guild.id)
        return settings.get_channel("pigeon")

    @commands.Cog.listener()
    async def on_ready(self):
        Pigeon.emojis["gold"] = self.bot.gold_emoji
        self.start_task(self.date_ticker, check = self.bot.production)
        self.start_task(self.fight_ticker, check = self.bot.production)
        await asyncio.sleep(60 * 60)
        self.start_task(self.stats_ticker, check = self.bot.production)

    def pigeon_check(self, ctx, member = None, name = "pigeon", human = None):
        cmd = ctx.invoked_subcommand or ctx.command
        command_name = cmd.name
        pigeon = None
        if command_name not in self.subcommands_no_require_pigeon:
            pigeon = get_active_pigeon(member or ctx.author, human = human)
            setattr(ctx, name, pigeon)
            pigeon_raise_if_not_exist(ctx, pigeon, name = name)

            if pigeon.status == Pigeon.Status.idle:
                #TODO: optimize.
                activities = []
                activities.append(pigeon.explorations.where(Exploration.finished == False))
                activities.append(pigeon.outbox.where(Mail.finished == False))
                activities.append(pigeon.fights.where(Fight.finished == False))

                for activity_group in activities:
                    for activity in activity_group:
                        activity.finished = True
                        activity.save()

        if command_name not in self.subcommands_no_require_available:
            pigeon_raise_if_unavailable(ctx, pigeon, name = name)
        if command_name not in self.subcommands_no_require_stats:
            pigeon_raise_if_stats_too_low(ctx, pigeon, name = name)
        return pigeon

    @commands.group()
    async def pigeon(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

        ctx.human = ctx.get_human()
        for message in list(ctx.human.system_messages.where(SystemMessage.read == False)):
            await ctx.send(embed = message.embed)
            message.read = True
            message.save()
            # return

        self.pigeon_check(ctx, human = ctx.human)

    @pigeon.command(name = "buy")
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_buy(self, ctx, member : discord.Member = None):
        """Buy a pigeon."""
        member = member or ctx.author
        human = ctx.get_human(user = member)
        pigeon = get_active_pigeon(member, human = human)

        if pigeon is not None:
            return asyncio.gather(ctx.send(ctx.translate("pigeon_already_purchased").format(name = pigeon.name)))

        pigeon = Pigeon(human = human)
        await pigeon.editor_for(ctx, "name")
        pigeon.save()

        cost = 50
        ctx.human.gold -= cost
        ctx.human.save()

        embed = self.get_base_embed(ctx.guild)
        winnings_value = "\n"+(get_winnings_value(gold = -cost))
        if member.id != ctx.author.id:
            embed.description = ctx.translate("pigeon_purchased_for").format(member = member) + winnings_value
        else:
            embed.description = ctx.translate("pigeon_purchased") + winnings_value
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "languages", aliases = ["lang"])
    async def pigeon_languages(self, ctx):
        table = Table(padding = 0)
        table.add_row(Row(["name", "%", "rank"], header = True))

        for language_mastery in ctx.pigeon.language_masteries.order_by(LanguageMastery.mastery.desc()):
            values = [str(language_mastery.language.name), str(language_mastery.mastery)+"%", str(language_mastery.rank)]
            table.add_row(Row(values))

        await table.to_paginator(ctx, 15).wait()

    @pigeon.command(name = "gender")
    async def pigeon_gender(self, ctx, gender : EnumConverter(Gender)):
        ctx.pigeon.gender = gender
        ctx.pigeon.save()
        asyncio.gather(ctx.send(ctx.translate("gender_set").format(gender = gender.name)))

    @pigeon.command(name = "name", aliases = ["rename"])
    async def pigeon_name(self, ctx):
        cost = 50
        ctx.raise_if_not_enough_gold(cost, ctx.pigeon.human)
        await ctx.pigeon.editor_for(ctx, "name")
        ctx.pigeon.save()
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Name has been set to {ctx.pigeon.name}" + "\n" + get_winnings_value(gold = -cost)
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "challenge", aliases = ["fight"])
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_challenge(self, ctx, member : discord.Member):
        """Challenge another user to a fight."""
        channel = self.get_pigeon_channel(ctx.guild)
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_challenge_self"))

        ctx.pigeon1 = ctx.pigeon
        self.pigeon_check(ctx, member, name = "pigeon2")

        fight = Fight(
            guild_id = ctx.guild.id,
            start_date = None,
            pigeon1 = ctx.pigeon,
            pigeon2 = ctx.pigeon2
        )

        await fight.editor_for(ctx, "bet", min = 0, max = min([ctx.pigeon1.human.gold, ctx.pigeon2.human.gold]), skippable = True)

        ctx.raise_if_not_enough_gold(fight.bet, ctx.pigeon1.human, name = "pigeon1")
        ctx.raise_if_not_enough_gold(fight.bet, ctx.pigeon2.human, name = "pigeon2")

        fight.save()

        for pigeon in fight.pigeons:
            pigeon.status = Pigeon.Status.fighting
            pigeon.save()

        embed = self.get_base_embed(ctx.guild)
        embed.title = "Pigeon Challenge"
        embed.description = f"{ctx.pigeon1.name} has challenged {ctx.pigeon2.name} to a pigeon fight.\nThe stake for this fight is `{fight.bet}`"

        footer = []
        footer.append(f"use '{ctx.prefix}pigeon accept' to accept")
        footer.append(f"or '{ctx.prefix}pigeon reject' to reject")
        embed.set_footer(text = "\n".join(footer))
        asyncio.gather(channel.send(embed = embed)) 

    @pigeon.command(name = "date")
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_date(self, ctx, member : discord.Member ):
        """Have your pigeon date another pigeon"""
        if member.id == self.bot.owner_id or ctx.author.id == self.bot.owner_id:
            raise SendableException(ctx.translate("pigeon_undateable"))

        channel = self.get_pigeon_channel(ctx.guild)
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_date_self"))

        self.pigeon_check(ctx, member, name = "pigeon2")
        pigeon1 = ctx.pigeon
        pigeon2 = ctx.pigeon2

        date = Date(guild_id = ctx.guild.id, start_date = None, pigeon1 = pigeon1, pigeon2 = pigeon2)

        date.save()

        for pigeon in (date.pigeon1, date.pigeon2):
            pigeon.status = Pigeon.Status.dating
            pigeon.save()

        embed = self.get_base_embed(ctx.guild)
        embed.title = "Pigeon Dating"
        embed.description = f"{pigeon1.name} has invited {pigeon2.name} to a date."
        footer = []
        footer.append(f"use '{ctx.prefix}pigeon accept' to accept")
        footer.append(f"or '{ctx.prefix}pigeon reject' to reject")
        embed.set_footer(text = "\n".join(footer))
        asyncio.gather(channel.send(embed = embed))

    @pigeon.command(name = "accept")
    async def pigeon_accept(self, ctx):
        pigeon2 = ctx.pigeon

        challenge = pigeon2.current_activity
        if not isinstance(challenge, (Date, Fight)) or challenge.pigeon1 == pigeon2:
            raise SendableException(ctx.translate("nothing_to_accept"))

        error_messages = challenge.validate(ctx)
        if error_messages is not None and len(error_messages) > 0:
            challenge.delete_instance()
            raise SendableException(error_messages[0])

        if isinstance(challenge, Fight):
            for pigeon in challenge.pigeons:
                human = pigeon.human
                human.gold -= challenge.bet
                human.save()

        challenge.accepted   = True
        challenge.start_date = datetime.datetime.utcnow()
        challenge.end_date   = challenge.start_date + datetime.timedelta(minutes = 5)
        challenge.save()

        embed = self.get_base_embed(ctx.guild)

        lines = []
        lines.append(f"{ctx.author.mention} has accepted the {challenge.type.lower()}!")
        lines.append(f"The pigeons have now started {challenge.pigeon1.status.name.lower()}.")
        embed.description = "\n".join(lines)
        embed.set_footer(text = f"{challenge.type} will end at", icon_url = challenge.icon_url)
        embed.timestamp = challenge.end_date

        channel = self.get_pigeon_channel(ctx.guild)
        await channel.send(embed = embed)

    @pigeon.command(name = "reject", aliases = ["deny", "cancel"])
    async def pigeon_reject(self, ctx):
        pigeon = ctx.pigeon

        challenge = pigeon.current_activity

        if not isinstance(challenge, (Date, Fight)):
            raise SendableException(ctx.translate("nothing_to_reject"))

        if challenge.accepted:
            raise SendableException(ctx.translate("already_accepted"))

        challenge.accepted = False
        challenge.save()

        for pigeon in challenge.pigeons:
            pigeon.status = Pigeon.Status.idle
            pigeon.save()

        embed = self.get_base_embed(ctx.guild)
        embed.description = f"{ctx.author.mention} has rejected the {challenge.type.lower()}!"
        channel = self.get_pigeon_channel(ctx.guild)
        await channel.send(content = f"{challenge.pigeon1.human.user.mention} | {challenge.pigeon2.human.user.mention}", embed = embed)

    @pigeon.command(name = "relationships")
    async def pigeon_relationships(self, ctx):
        query = PigeonRelationship.select()
        query = query.where((PigeonRelationship.pigeon1 == ctx.pigeon) | (PigeonRelationship.pigeon2 == ctx.pigeon))

        table = Table(padding = 0)
        table.add_row(Row(["name2", "score", "title"], header = True))

        for relationship in query:
            other = relationship.pigeon1 if relationship.pigeon1 != ctx.pigeon else relationship.pigeon2
            values = [other.name, relationship.score, relationship.title]
            table.add_row(Row(values))

        await table.to_paginator(ctx, 15).wait()

    @pigeon.command(name = "explore")
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_explore(self, ctx):
        """Have your pigeon exploring a random location."""
        pigeon = ctx.pigeon

        residence = pigeon.human.country or Country.random()
        destination = Country.random()

        exploration = Exploration(residence = residence, destination = destination, pigeon = pigeon)
        exploration.end_date = exploration.start_date + datetime.timedelta(minutes = exploration.calculate_duration())
        pigeon.status = Pigeon.Status.exploring
        pigeon.save()
        exploration.save()

        remind_emoji = "❗"
        embed = self.get_base_embed(ctx.guild)
        embed.description = "Okay. Your pigeon is now off to explore a random location!"
        embed.set_footer(text = f"React with {remind_emoji} to get reminded when available.\n'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        message = await ctx.send(embed = embed)

        waiter = ReactionWaiter(ctx, message, emojis = (remind_emoji,), members = (ctx.author, ))
        await waiter.add_reactions()
        emoji = await waiter.wait(remove = True)
        await waiter.clear_reactions()
        if emoji is not None:
            Reminder.create(
                user_id    = ctx.author.id,
                channel_id = ctx.channel.id,
                text       = ctx.translate("pigeon_ready_to_be_retrieved"),
                due_date   = exploration.end_date
            )
            asyncio.gather(ctx.success(ctx.translate("reminder_created")))

    @pigeon.command(name = "retrieve", aliases = ["return"] )
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_retrieve(self, ctx):
        """Retrieve and check on your pigeon."""
        pigeon = ctx.pigeon
        if pigeon.status == Pigeon.Status.idle:
            raise SendableException(ctx.translate("pigeon_idle"))

        embed = self.get_base_embed(ctx.guild)

        activity = pigeon.current_activity

        if activity is None:
            raise SendableException(ctx.translate("nothing_to_retrieve"))

        if isinstance(activity, Exploration):
            if activity.end_date_passed:
                def run():
                    retrieval = ExplorationRetrieval(activity)
                    embed = retrieval.embed
                    retrieval.commit()
                    return asyncio.gather(ctx.send(embed = embed))
                ctx.bot.profile(run)
                return
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to explore!"
                embed.set_footer(text = "Check back at", icon_url = "https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date
                return asyncio.gather(ctx.send(embed = embed))
        elif isinstance(activity, Mail):
            if activity.end_date_passed:
                retrieval = MailRetrieval(activity)
                embed = retrieval.embed
                retrieval.commit()
                return asyncio.gather(ctx.send(embed = embed))
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to send a message!"
                embed.set_footer(text = "Check back at", icon_url = "https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date
                return asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "mail", aliases = ["message", "send", "letter"])
    @commands.max_concurrency(1, per = commands.BucketType.user)
    async def pigeon_mail(self, ctx, user : discord.User):
        """Send someone a pigeon letter."""
        if user.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_send_to_self"))

        sender = ctx.pigeon

        await ctx.send(ctx.translate("check_dms"))
        ctx.channel = ctx.author.dm_channel
        if ctx.channel is None:
            ctx.channel = await ctx.author.create_dm()

        recipient = ctx.get_human(user = user)

        mail = Mail(recipient = recipient, sender = sender, read = False)

        await mail.editor_for(ctx, "message")
        await mail.editor_for(ctx, "gold", min = 0, max = sender.human.gold, skippable = True)

        waiter = ItemWaiter(ctx, prompt = ctx.translate("mail_item_prompt"), skippable = True)
        mail.item = await waiter.wait()

        human_item, _ = HumanItem.get_or_create(item = mail.item, human = sender.human)
        if human_item.amount < 1:
            raise SendableException(ctx.translate("item_not_found"))

        human_item.amount -= 1
        human_item.save()

        mail.residence   = sender.human.country
        mail.destination = recipient.country
        mail.end_date = mail.start_date + datetime.timedelta(minutes = mail.calculate_duration())
        sender.human.gold -= mail.gold
        sender.status = Pigeon.Status.mailing

        mail.save()
        sender.human.save()
        sender.save()

        remind_emoji = "❗"
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Your pigeon is off to send a package to {recipient.mention}!"
        embed.set_footer(text = f"React with {remind_emoji} to get reminded when available.\n'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        message = await ctx.send(embed = embed)

        waiter = ReactionWaiter(ctx, message, emojis = (remind_emoji,), members = (ctx.author, ))
        await waiter.add_reactions()
        emoji = await waiter.wait(remove = True)
        if emoji is not None:
            Reminder.create(
                user_id    = ctx.author.id,
                channel_id = ctx.channel.id,
                text       = ctx.translate("pigeon_ready_to_be_retrieved"),
                due_date   = mail.end_date
            )
            asyncio.gather(ctx.success(ctx.translate("reminder_created")))

    @commands.command()
    async def inbox(self, ctx):
        """Check your inbox."""
        human = ctx.get_human()
        unread_mail = human.inbox.where(Mail.read == False).where(Mail.finished == True)
        if len(unread_mail) == 0:
            return await ctx.send(ctx.translate("no_unread_mail"))

        for mail in list(unread_mail):
            embed = self.get_base_embed(ctx.guild)
            embed.set_author(
                name = f"You've got mail from {mail.sender.human.user}!",
                icon_url = mail.sender.human.user.avatar_url
            )

            if mail.message is not None:
                embed.add_field(name = "📜 message", value = mail.message, inline = False)
            if mail.gold > 0:
                embed.add_field(name = f"{Pigeon.emojis['gold']} gold", value = f"{mail.gold}", inline = False)
            if mail.item is not None:
                lines = []
                lines.append(mail.item.name)
                if mail.item.usable:
                    lines.append(f"*{mail.item.description}*")
                embed.add_field(name = "🎁 gift", value = "\n".join(lines), inline = False)
                embed.set_thumbnail(url = mail.item.image_url)

            await ctx.send(embed = embed)

            mail.read = True
            mail.save()
            if mail.gold > 0:
                mail.recipient.gold += mail.gold
                mail.recipient.save()
            if mail.item is not None:
                human_item, _ = HumanItem.get_or_create(item = mail.item, human = mail.recipient)
                human_item.amount += 1
                human_item.save()

    @pigeon.command(name = "stats")
    async def pigeon_stats(self, ctx, member : discord.Member = None):

        if member is not None:
            self.pigeon_check(ctx, member)

        member = member or ctx.author

        pigeon = ctx.pigeon
        embed = self.get_base_embed(ctx.guild)

        query = f"""
            SELECT COUNT(DISTINCT destination) as unique_countries_visited, COUNT(*) as total_countries_visited
            FROM exploration
            WHERE pigeon_id = {pigeon.id}
            AND finished = 1;
        """

        cursor = database.execute_sql(query)
        unique_countries_visited, total_countries_visited = cursor.fetchone()

        lines = []
        lines.append(f"Total explorations: {total_countries_visited}")
        lines.append(f"Unique countries visited: {unique_countries_visited}")

        embed.add_field(name = f"Explorations {Pigeon.Status.exploring.value}", value = "\n".join(lines), inline = False)

        query = f"""
        SELECT SUM(gold) as total_gold_sent, count(id) as mails_sent
        FROM mail WHERE sender_id = {pigeon.id} AND finished = 1"""

        cursor = database.execute_sql(query)
        total_gold_sent, mails_sent = cursor.fetchone()

        lines = []
        lines.append(f"Total mails sent: {mails_sent}")
        lines.append(f"Total gold sent: {total_gold_sent}")
        embed.add_field(name = f"Mails {Pigeon.Status.mailing.value}", value = "\n".join(lines), inline = False)

        query = f"""
            SELECT gold_won, -gold_lost, fights_won, fights_lost FROM
            (SELECT SUM(bet) as gold_won, count(*) as fights_won
            FROM fight
            WHERE finished = 1 AND (pigeon1_id = {pigeon.id} OR pigeon2_id = {pigeon.id})
            AND ( (pigeon1_id = {pigeon.id} AND won = 1) OR (pigeon2_id = {pigeon.id} AND won = 0))
            ) as f1,

            (SELECT SUM(bet) as gold_lost, count(*) as fights_lost
            FROM fight
            WHERE finished = 1 AND (pigeon1_id = {pigeon.id} OR pigeon2_id = {pigeon.id})
            AND ( (pigeon1_id = {pigeon.id} AND won = 0) OR (pigeon2_id = {pigeon.id} AND won = 1))
            ) as f2;
        """

        cursor = database.execute_sql(query)
        gold_won, gold_lost, fights_won, fights_lost = cursor.fetchone()
        profit = gold_won + gold_lost

        lines = []
        lines.append(f"Total fights won : {fights_won}")
        lines.append(f"Total fights lost: {fights_lost}")
        lines.append(f"Profit: {profit}")
        embed.add_field(name = f"Fights {Pigeon.Status.fighting.value}", value = "\n".join(lines), inline = False)

        in_possession = HumanItem.select().where(HumanItem.human == pigeon.human).where(HumanItem.amount > 0).count()
        total_items = Item.select().count()
        lines = []
        lines.append(f"Items {in_possession} / {total_items}")
        embed.add_field(name = f"Human", value = "\n".join(lines), inline = False)

        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "history")
    async def pigeon_history(self, ctx, member : discord.Member = None):
        member = member or ctx.author
        query = Pigeon.select()
        query = query.where(Pigeon.human == ctx.get_human(user = member))
        query = query.where(Pigeon.condition != Pigeon.Condition.active)

        lines = []

        for pigeon in query:
            lines.append(pigeon.name)
        asyncio.gather(ctx.send("```\n{}```".format("\n".join(lines))))

    @pigeon.command(name = "status")
    async def pigeon_status(self, ctx, member : discord.Member = None):
        """Check the status of your pigeon."""
        if member is not None:
            self.pigeon_check(ctx, member = member)

        pigeon = ctx.pigeon

        data = {}
        emojis = []

        for attr, emoji in Pigeon.emojis.items():
            try:
                value = getattr(pigeon, attr)
            except AttributeError:
                continue
            if isinstance(getattr(Pigeon, attr), PercentageField):
                data[attr] = f"{value}%"
            else:
                data[attr] = f"{value}"
            emojis.append(emoji)

        emojis.append(pigeon.status.value)
        data["status"] = pigeon.status.name
        lines = prettify_dict(data, emojis = emojis)
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"```\n{lines}```"

        lines = []
        for pigeon_buff in pigeon.buffs:
            buff = pigeon_buff.buff
            lines.append(f"**{buff.name}**: *{buff.description}*")
        if len(lines) > 0:
            embed.add_field(name = "Buffs", value = "\n".join(lines))

        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "scoreboard")
    async def pigeon_scoreboard(self, ctx):
        query = Pigeon.select()
        query = query.join(Human, on = (Pigeon.human == Human.id) )
        query = query.join(Earthling, on = (Human.id == Earthling.human) )
        query = query.where(Pigeon.condition == Pigeon.Condition.active)
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.order_by(Pigeon.experience.desc())

        table = Table(padding = 0)
        table.add_row(Row(["rank", "exp", "pigeon", "owner"], header = True))

        i = 0
        for pigeon in query:
            user = pigeon.human.user
            if user is None:
                continue
            values = [f"{i+1}", str(pigeon.experience), limit_str(pigeon.name, 10), limit_str(user, 10)]
            table.add_row(Row(values))
            i += 1

        await table.to_paginator(ctx, 15).wait()

    def increase_stats(self, ctx, attr_name, attr_increase, cost, message):
        pigeon = ctx.pigeon

        value = getattr(pigeon, attr_name)
        if value == 100:
            ctx.command.reset_cooldown(ctx)
            raise SendableException(ctx.translate(f"{attr_name}_already_max"))
        try:
            ctx.raise_if_not_enough_gold(cost, pigeon.human)
        except SendableException:
            ctx.command.reset_cooldown(ctx)
            raise

        pigeon.update_stats({attr_name : attr_increase, "gold": -cost})

        embed = self.get_base_embed(ctx.guild )
        embed.description = message.format(pigeon = pigeon)
        embed.description += get_winnings_value(**{attr_name : attr_increase, "gold" : -cost})
        asyncio.gather(ctx.send(embed = embed))

    @commands.cooldown(1, (45 * 60), type=commands.BucketType.user)
    @pigeon.command(name = "clean")
    async def pigeon_clean(self, ctx):
        self.increase_stats(ctx, "cleanliness", 25, 15, "You happily clean up the fecal matter of `{pigeon.name}`.\n")

    @commands.cooldown(1, (45 * 60), type=commands.BucketType.user)
    @pigeon.command(name = "feed")
    async def pigeon_feed(self, ctx):
        self.increase_stats(ctx, "food", 25, 15, "You feed `{pigeon.name}` some seeds and whatever else they eat.\n")

    @commands.cooldown(1, (45 * 60), type=commands.BucketType.user)
    @pigeon.command(name = "heal")
    async def pigeon_heal(self, ctx):
        self.increase_stats(ctx, "health", 20, 15, "You give `{pigeon.name}` some seed you found inside your couch and convince it of its healing effects.\n")

    @commands.cooldown(1, (3600 * 2), type=commands.BucketType.user)
    @pigeon.command(name = "play")
    async def pigeon_play(self, ctx):
        self.increase_stats(ctx, "happiness", 20, 15, "You play a game of tennis with your pigeon. `{pigeon.name}` happily falls asleep.\n")

    @pigeon.command(name = "help")
    async def pigeon_help(self, ctx):
        await ctx.send_help(ctx.command.root_parent)

    @pigeon.command()
    @commands.cooldown(1, (3600 * 1), type = commands.BucketType.user)
    async def poop(self, ctx, member : discord.Member):
        self.pigeon_check(ctx, member, name = "pigeon2")
        relationship = PigeonRelationship.get_or_create_for(ctx.pigeon, ctx.pigeon2)
        price = 5
        relationship.score -= price
        relationship.save()

        embed = self.get_base_embed(ctx.guild)
        lines = []
        lines.append(f"Your pigeon successfully poops on `{ctx.pigeon2.name}`")
        lines.append(f"And to finish it off, `{ctx.pigeon.name}` wipes {ctx.pigeon.gender.get_posessive_pronoun()} butt clean on {ctx.pigeon2.gender.get_posessive_pronoun()} fur.")
        lines.append("")

        lines.append(ctx.pigeon.name)
        data1 = {"cleanliness": 5}
        lines.append(get_winnings_value(**data1))
        ctx.pigeon.update_stats(data1)

        lines.append(ctx.pigeon2.name)
        data2 = {"cleanliness": -10}
        lines.append(get_winnings_value(**data2))
        ctx.pigeon2.update_stats(data2)

        embed.description = "\n".join(lines)

        embed.set_footer(text = f"-{price} relations")
        await ctx.send(embed = embed)

    @tasks.loop(seconds=30)
    async def date_ticker(self):
        with database.connection_context():
            query = Date.select()
            query = query.where(Date.finished == False)
            query = query.where(Date.accepted == True)
            query = query.where(Date.end_date <= datetime.datetime.utcnow())

            for date in query:
                guild = date.guild
                channel = self.get_pigeon_channel(guild)

                embed = self.get_base_embed(guild)

                score = 0
                lines = []
                for pigeon in (date.pigeon1, date.pigeon2):
                    other = date.pigeon1 if pigeon == date.pigeon2 else date.pigeon2

                    if pigeon.cleanliness >= 60:
                        lines.append(f"{pigeon.name} smells like fresh fries, delicious (+10)")
                        score += 10
                    elif pigeon.cleanliness >= 40:
                        lines.append(f"{pigeon.name} has a slight body odor, but it's tolerable (+0)")
                    elif pigeon.cleanliness >= 20:
                        lines.append(f"{pigeon.name} has a clear body odor. (-10)")
                        score -= 10
                    else:
                        lines.append(f"{pigeon.name} is caked in feces, absolutely disgusting! (-20)")
                        score -= 20

                    if pigeon.food >= 60:
                        lines.append(f"{pigeon.name} ellegantly and majestically enjoys {pigeon.gender.get_posessive_pronoun()} fry. (+10)")
                        score += 10
                    elif pigeon.food >= 30:
                        lines.append(f"{pigeon.name} is clearly a bit hungry but still manages to (barely) not embarrass {pigeon.gender.get_pronoun(object = True)}self (+0)")
                    else:
                        lines.append(f"{pigeon.name} is starving. As soon as {pigeon.gender.get_pronoun()} sees a fry {pigeon.gender.get_pronoun()} starts to drool, runs at it like a wild animal and devours it in one go. How unappealing. (-10)")
                        score -= 10

                    if pigeon.health <= 30:
                        lines.append(f"{pigeon.name} is covered in blood. {pigeon.gender.get_pronoun()} tries to make it work but accidentally drips some blood on {other.name}s fry . Not a good sauce. (-10)")
                        score -= 10

                    if pigeon.happiness >= 60:
                        lines.append(f"{pigeon.name} smiled in confidence the entire date. (+10)")
                        score += 10
                    elif pigeon.happiness >= 30:
                        lines.append(f"{pigeon.name} was clearly not in his best spirits. Slightly bringing his date down as well. (-5)")
                        score -= 5
                    else:
                        lines.append(f"{pigeon.name} is miserable. From the start, {pigeon.gender.get_pronoun()} starts asking what the point of this date even is, what the point of anything is, and why {pigeon.gender.get_pronoun()} should even bother eating at all. (-10)")
                        score -= 10

                lines = "\n- " + ("\n\n- ".join(lines))
                embed.description = f"{lines}\n\nScore: **{score}**"
                embed.set_footer(text = f"{score // 10} relations")
                asyncio.gather(channel.send(embed = embed))

                for pigeon in date.pigeons:
                    pigeon.status = Pigeon.Status.idle
                    pigeon.save()

                date.score = score

                relationship = PigeonRelationship.get_or_create_for(date.pigeon1, date.pigeon2)
                relationship.score += date.score // 10
                relationship.save()

                date.finished = True
                date.save()

    @tasks.loop(seconds=30)
    async def fight_ticker(self):
        with database.connection_context():
            query = Fight.select()
            query = query.where(Fight.finished == False)
            query = query.where(Fight.accepted == True)
            query = query.where(Fight.end_date <= datetime.datetime.utcnow())
            for fight in query:
                won = random.randint(0, 1) == 0
                guild = fight.guild
                channel = self.get_pigeon_channel(guild)

                if won:
                    winner = fight.challenger
                    loser = fight.challengee
                else:
                    winner = fight.challengee
                    loser = fight.challenger

                embed = self.get_base_embed(guild)
                embed.description = f"`{winner.name}` creeps into `{loser.name}`’s room. `{winner.name}`’s jaw unhinges and swallows `{loser.name}` whole."

                winner_data = {"experience" : 30, "health" : -10}
                loser_data = {"experience" : 5, "health" : -25}

                embed.add_field(
                    name = f"💩 {loser.name} ({loser.human.user})",
                    value = get_winnings_value(**loser_data, gold = -fight.bet)
                )
                embed.add_field(
                    name = f"🏆 {winner.name} ({winner.human.user})",
                    value = get_winnings_value(**winner_data, gold = fight.bet)
                )

                asyncio.gather(channel.send(content = f"{winner.human.mention} | {loser.human.mention}", embed = embed))

                winner.status = Pigeon.Status.idle
                loser.status = Pigeon.Status.idle

                winner_data["gold"] = fight.bet*2
                winner.update_stats(winner_data)
                loser.update_stats(loser_data)

                fight.won = won
                fight.finished = True
                fight.save()

    @tasks.loop(hours = 1)
    async def stats_ticker(self):
        with database.connection_context():
            query = Pigeon.select()
            query = query.where(Pigeon.condition == Pigeon.Condition.active)
            query = query.where(Pigeon.status == Pigeon.Status.idle)

            for pigeon in query:
                data = {
                    "food"        : -1,
                    "health"      : -0,
                    "happiness"   : -1,
                    "cleanliness" : -1,
                }

                for pigeon_buff in pigeon.buffs:
                    if pigeon_buff.buff.code == "fully_fed":
                        data["food"] = 0
                    if pigeon_buff.buff.code == "bleeding":
                        data["health"] += -2

                if pigeon.food <= 20 or pigeon.cleanliness <= 20:
                    data["health"] += -1
                if pigeon.food == 0:
                    data["health"] += -2

                pigeon.update_stats(data)
                pigeon.save()

def get_winnings_value(**kwargs):
    lines = []
    for key, value in kwargs.items():
        if value != 0:
            lines.append(f"{Pigeon.emojis[key]} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)

def get_winnings_value_included(pigeon, **kwargs):
    lines = []
    for key, value in kwargs.items():
        if value != 0:
            if key == "gold":
                current_value = pigeon.human.gold
            else:
                current_value = getattr(pigeon, key)
            new_value = current_value + value

            lines.append(f"{Pigeon.emojis[key]} {current_value}/{new_value} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)

def get_active_pigeon(user, raise_on_none = False, human = None):
    try:
        return Pigeon.get(human = human or config.bot.get_human(user = user), condition = Pigeon.Condition.active)
    except Pigeon.DoesNotExist:
        return None

def pigeon_raise_if_not_exist(ctx, pigeon, name = "pigeon"):
    if pigeon is None:
        ctx.command.reset_cooldown(ctx)
        raise SendableException(ctx.translate(f"{name}_does_not_exist"))

def pigeon_raise_if_unavailable(ctx, pigeon, name = "pigeon"):
    pigeon_raise_if_not_exist(ctx, pigeon, name)
    if pigeon.status != Pigeon.Status.idle:
        ctx.command.reset_cooldown(ctx)
        raise SendableException(ctx.translate(f"{name}_not_idle").format(status = pigeon.status.name))

def pigeon_raise_if_stats_too_low(ctx, pigeon, name = "pigeon"):
    if pigeon.cleanliness <= 10:
        message = ctx.translate(f"{name}_too_stinky")
    elif pigeon.happiness <= 10:
        message = ctx.translate(f"{name}_too_sad")
    elif pigeon.food <= 10:
        message = ctx.translate(f"{name}_too_hungry")
    elif pigeon.health <= 10:
        message = ctx.translate(f"{name}_too_wounded")
    else:
        return
    ctx.command.reset_cooldown(ctx)
    raise SendableException(message.format(pigeon = pigeon))

def setup(bot):
    bot.add_cog(PigeonCog(bot))