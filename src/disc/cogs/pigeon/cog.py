import random

from discord.ext import commands, tasks

from src.config import config
from src.constants import BR, GOLD_EMOJI
from src.disc.cogs.core import BaseCog
from src.disc.errors.base import SendableException
from src.disc.helpers.converters import EnumConverter
from src.disc.helpers.paginating import Paginator
from src.disc.helpers.pretty import Row, Table, limit_str
from src.disc.helpers.waiters import *
from src.models import (Date, Earthling, Exploration, Fight, Human,
                        HumanItem, Item, LanguageMastery, Mail, Pigeon,
                        PigeonRelationship, Reminder, SystemMessage, database)
from src.utils.country import Country
from src.utils.enums import Gender
from .exploration_retrieval import ExplorationRetrieval, MailRetrieval
from ...helpers.known_guilds import KnownGuild


class ItemWaiter(StrWaiter):
    def __init__(self, ctx, in_inventory=True, **kwargs):
        super().__init__(ctx, max_words=None, **kwargs)
        self.show_instructions = False
        self.case_sensitive = False
        self.item_mapping = {}
        self.in_inventory = in_inventory
        self.table = None

        if in_inventory:
            query = f"""
            SELECT
            item.id as id, item.name as item_name, human_item.amount as amount
            FROM
            human_item
            INNER JOIN item ON human_item.item_id = item.id
            WHERE human_id = {ctx.get_human()}
            AND amount > 0
            """

            cursor = database.execute_sql(query)

            data = [("name", "amount")]
            for id, item_name, amount in cursor:
                self.allowed_words.append(item_name.lower())
                data.append((item_name, amount))
                self.item_mapping[item_name.lower()] = id
        else:
            data = [("name",)]
            for item in Item.select(Item.id, Item.name):
                data.append((item.name,))
                self.allowed_words.append(item.name.lower())
                self.item_mapping[item.name.lower()] = item.id

        self.table = Table.from_list(data, first_header=True)

    async def wait(self, *args, **kwargs):
        asyncio.gather(self.table.to_paginator(self.ctx, 15).wait())
        await asyncio.sleep(0.5)
        return await super().wait(*args, **kwargs)

    def convert(self, argument):
        id = self.item_mapping.get(argument.lower())
        if id is None:
            raise ConversionFailed("Item not found.")
        return id


class PigeonCog(BaseCog, name="Pigeon"):
    subcommands_no_require_pigeon = [
        "buy",
        "history",
        "scoreboard",
        "help",
        "inbox",
        "pigeon",
    ]

    subcommands_pvp_only = [
        "rob"
    ]

    subcommands_no_require_available = [
                                           "status",
                                           "relationships",
                                           "reject",
                                           "stats",
                                           "dating",
                                           "setup",
                                           "languages",
                                           "storytime",
                                           "retrieve",
                                           "gender",
                                           "name",
                                           "accept",
                                           "pvp",
                                       ] + subcommands_no_require_pigeon

    subcommands_no_require_stats = [
                                       "heal",
                                       "clean",
                                       "feed",
                                       "play",
                                       "date",
                                       "rob",
                                       "poop",
                                   ] + subcommands_no_require_available

    def __init__(self, bot):
        super().__init__(bot)
        self.message_counts = {}

    def get_base_embed(self, guild):
        embed = discord.Embed(color=self.bot.get_dominant_color(guild))
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed

    def get_pigeon_channel(self, guild):
        if guild.id == KnownGuild.crossroads:
            return guild.get_channel(1241342425193123850)

        for channel in guild.text_channels:
            if 'bot-spam' in channel.name.lower():
                return channel
            if 'bot-playground' in channel.name.lower():
                return channel
            if 'bot-commands' in channel.name.lower():
                return channel
            if 'bot' in channel.name.lower():
                return channel

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.date_ticker, check=self.bot.production)
        self.start_task(self.fight_ticker, check=self.bot.production)
        await asyncio.sleep(60 * 60)
        # self.start_task(self.stats_ticker, check = self.bot.production)

    def pigeon_check(self, ctx, member=None, name="pigeon", human=None):
        cmd = ctx.invoked_subcommand or ctx.command
        command_name = cmd.name
        pigeon = None
        if command_name not in self.subcommands_no_require_pigeon:
            pigeon = get_active_pigeon(member or ctx.author, human=human)
            setattr(ctx, name, pigeon)
            pigeon_raise_if_not_exist(ctx, pigeon, name=name)

            if pigeon.is_jailed:
                raise SendableException(ctx.translate(f"{name}_pigeon_jailed"))

            if pigeon.status == Pigeon.Status.idle:
                query = f"""
                SELECT
                legacy_exploration.id as exploration_id, mail.id as mail_id, fight.id as fight_id, date.id as date_id
                FROM
                pigeon
                LEFT JOIN legacy_exploration
                    ON (legacy_exploration.pigeon_id = pigeon.id AND legacy_exploration.finished = 0)
                LEFT JOIN mail
                    ON (mail.sender_id = pigeon.id AND mail.finished = 0)
                LEFT JOIN fight
                    ON ((fight.pigeon1_id = pigeon.id OR fight.pigeon2_id = pigeon.id) AND fight.finished = 0)
                LEFT JOIN date
                    ON ((date.pigeon1_id = pigeon.id OR date.pigeon2_id = pigeon.id) AND date.finished = 0)
                WHERE pigeon.id = {pigeon.id}
                """

                cursor = database.execute_sql(query)
                for row in cursor:
                    classes = [Exploration, Mail, Fight, Date]
                    i = 0
                    for id in row:
                        if id is not None:
                            cls = classes[i]
                            cls.update(finished=True).where(cls.id == id).execute()
                        i += 1

        if command_name not in self.subcommands_no_require_available:
            pigeon_raise_if_unavailable(ctx, pigeon, name=name)
        if command_name not in self.subcommands_no_require_stats:
            pigeon_raise_if_stats_too_low(ctx, pigeon, name=name)
        if command_name in self.subcommands_pvp_only and not pigeon.pvp:
            raise SendableException(ctx.translate(f"{name}_pvp_not_enabled"))

        return pigeon

    @commands.group()
    async def pigeon(self, ctx):
        ctx.human = ctx.get_human()
        for message in list(ctx.human.system_messages.where(SystemMessage.read == False)):
            await ctx.send(embed=message.embed)
            message.read = True
            message.save()

        self.pigeon_check(ctx, human=ctx.human)

    @pigeon.command(name="languages", aliases=["lang"])
    async def pigeon_languages(self, ctx):
        """View what languages your pigeon knows."""
        table = Table(padding=0)
        table.add_row(Row(["name", "%", "rank"], header=True))

        for language_mastery in ctx.pigeon.language_masteries.order_by(LanguageMastery.mastery.desc()):
            values = [str(language_mastery.language.name.replace(" (macrolanguage)", "")),
                      str(language_mastery.mastery) + "%", str(language_mastery.rank)]
            table.add_row(Row(values))

        await table.to_paginator(ctx, 15).wait()

    @pigeon.command(name="gender")
    async def pigeon_gender(self, ctx, gender: EnumConverter(Gender)):
        """Change your pigeons gender."""
        ctx.pigeon.gender = gender
        ctx.pigeon.save()
        asyncio.gather(ctx.send(ctx.translate("gender_set").format(gender=gender.name)))

    @pigeon.command(name="name", aliases=["rename"])
    async def pigeon_name(self, ctx):
        """Change your pigeons name."""
        cost = 50
        ctx.raise_if_not_enough_gold(cost, ctx.get_human())
        await ctx.pigeon.editor_for(ctx, "name")
        ctx.pigeon.save()
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Name has been set to {ctx.pigeon.name}" + "\n" + get_winnings_value(gold=-cost)
        asyncio.gather(ctx.send(embed=embed))

    @pigeon.command(name="fight")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pigeon_fight(self, ctx, member: discord.Member):
        """Fight other pigeons."""
        channel = self.get_pigeon_channel(ctx.guild)
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_challenge_self"))

        ctx.pigeon1 = ctx.pigeon
        self.pigeon_check(ctx, member, name="pigeon2")

        fight = Fight(
            guild_id=ctx.guild.id,
            start_date=None,
            pigeon1=ctx.pigeon,
            pigeon2=ctx.pigeon2
        )

        await fight.editor_for(ctx, "bet", min=0, max=min([ctx.pigeon1.human.gold, ctx.pigeon2.human.gold]),
                               skippable=True)

        ctx.raise_if_not_enough_gold(fight.bet, ctx.get_human(), name="pigeon1")
        ctx.raise_if_not_enough_gold(fight.bet, ctx.get_human(user=member), name="pigeon2")

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
        embed.set_footer(text="\n".join(footer))
        asyncio.gather(channel.send(embed=embed))

    @pigeon.command(name="pvp")
    async def pigeon_pvp(self, ctx):
        pigeon = ctx.pigeon

        if pigeon.pvp and not pigeon.can_disable_pvp:
            raise SendableException(ctx.translate("pvped_too_recently"))

        pigeon.pvp = not pigeon.pvp
        pigeon.save()
        asyncio.gather(ctx.send(f"Okay. PvP is now " + ("on" if pigeon.pvp else "off")))

    @pigeon.command(name="date")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pigeon_date(self, ctx, member: discord.Member):
        """Date other pigeons."""
        if member.id == self.bot.owner_id or ctx.author.id == self.bot.owner_id:
            raise SendableException(ctx.translate("pigeon_undateable"))

        channel = self.get_pigeon_channel(ctx.guild)
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_date_self"))

        self.pigeon_check(ctx, member, name="pigeon2")
        pigeon1 = ctx.pigeon
        pigeon2 = ctx.pigeon2

        date = Date(guild_id=ctx.guild.id, start_date=None, pigeon1=pigeon1, pigeon2=pigeon2)

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
        embed.set_footer(text="\n".join(footer))
        asyncio.gather(channel.send(embed=embed))

    @pigeon.command(name="accept")
    async def pigeon_accept(self, ctx):
        """Accept an invitation."""
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
                human = ctx.get_human(user=pigeon.human.user_id)
                human.gold -= challenge.bet
                human.save()

        challenge.accepted = True
        challenge.start_date = datetime.datetime.utcnow()
        challenge.end_date = challenge.start_date + datetime.timedelta(minutes=5)
        challenge.save()

        embed = self.get_base_embed(ctx.guild)

        lines = []
        lines.append(f"{ctx.author.mention} has accepted the {challenge.type.lower()}!")
        lines.append(f"The pigeons have now started {challenge.pigeon1.status.name.lower()}.")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"{challenge.type} will end at", icon_url=challenge.icon_url)
        embed.timestamp = challenge.end_date

        channel = self.get_pigeon_channel(ctx.guild)
        await channel.send(embed=embed)

    @pigeon.command(name="reject", aliases=["deny", "cancel"])
    async def pigeon_reject(self, ctx):
        """Reject an invitation."""
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
        await channel.send(content=f"{challenge.pigeon1.human.user.mention} | {challenge.pigeon2.human.user.mention}",
                           embed=embed)

    @pigeon.command(name="relationships")
    async def pigeon_relationships(self, ctx):
        """View your pigeons relationships."""

        query = """
SELECT
pigeon_relationship.score,
(CASE WHEN p1.id={pigeon_id} THEN p2.name ELSE p1.name END) as other_name
FROM pigeon_relationship
INNER JOIN pigeon p1 ON pigeon1_id = p1.id
INNER JOIN pigeon p2 ON pigeon2_id = p2.id
WHERE pigeon1_id = {pigeon_id} OR pigeon2_id = {pigeon_id}
ORDER BY score DESC;
        """

        table = Table(padding=0)
        table.add_row(Row(["name", "score", "title"], header=True))

        cursor = database.execute_sql(query.format(pigeon_id=ctx.pigeon.id))

        for score, other_name in cursor:
            values = [limit_str(other_name, 10), score, PigeonRelationship._get_title(score)]
            table.add_row(Row(values))

        await table.to_paginator(ctx, 15).wait()

    @pigeon.command(name="oldplore")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pigeon_oldplore(self, ctx):
        """Have your pigeon exploring countries."""
        pigeon = ctx.pigeon
        human = ctx.human

        residence = human.country or Country.random()
        destination = Country.random()

        exploration = Exploration(residence=residence, destination=destination, pigeon=pigeon)
        exploration.end_date = exploration.start_date + datetime.timedelta(minutes=exploration.calculate_duration())
        pigeon.status = Pigeon.Status.exploring
        pigeon.save()
        exploration.save()

        remind_emoji = "❗"
        embed = self.get_base_embed(ctx.guild)
        embed.description = "Okay. Your pigeon is now off to explore a random location!"
        embed.set_footer(
            text=f"React with {remind_emoji} to get reminded when available.\n'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        message = await ctx.send(embed=embed)

        waiter = ReactionWaiter(ctx, message, emojis=(remind_emoji,), members=(ctx.author,))
        await waiter.add_reactions()
        emoji = await waiter.wait(remove=True)
        await waiter.clear_reactions()
        if emoji is not None:
            Reminder.create(
                user_id=ctx.author.id,
                channel_id=ctx.channel.id,
                message=ctx.translate("pigeon_ready_to_be_retrieved"),
                due_date=exploration.end_date
            )
            asyncio.gather(ctx.success(ctx.translate("reminder_created")))

    @pigeon.command(name="retrieve", aliases=["return"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
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
                retrieval = ExplorationRetrieval(activity)
                embed = retrieval.embed
                retrieval.commit()
                return asyncio.gather(ctx.send(embed=embed))
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to explore!"
                embed.set_footer(text="Check back at",
                                 icon_url="https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                ts: datetime.datetime = activity.end_date
                embed.timestamp = ts.replace(tzinfo=datetime.timezone.utc)
                return asyncio.gather(ctx.send(embed=embed))
        elif isinstance(activity, Mail):
            if activity.end_date_passed:
                retrieval = MailRetrieval(activity)
                embed = retrieval.embed
                retrieval.commit()

                Reminder.create(
                    user_id=activity.recipient.user_id,
                    channel_id=None,
                    message=ctx.translate("pigeon_inbox_unread_mail"),
                    due_date=datetime.datetime.utcnow()
                )
                return asyncio.gather(ctx.send(embed=embed))
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to send a message!"
                embed.set_footer(text="Check back at",
                                 icon_url="https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date
                return asyncio.gather(ctx.send(embed=embed))

    @pigeon.command(name="mail", aliases=["message", "send", "letter"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def pigeon_mail(self, ctx, user: discord.User):
        """Sending someone a letter."""
        if user.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_send_to_self"))

        sender = ctx.pigeon

        await ctx.send(ctx.translate("check_dms"))
        ctx.channel = ctx.author.dm_channel
        if ctx.channel is None:
            ctx.channel = await ctx.author.create_dm()

        recipient = ctx.get_human(user=user)
        human = ctx.get_human()

        mail = Mail(recipient=recipient, sender=sender, read=False)

        await mail.editor_for(ctx, "message")
        await mail.editor_for(ctx, "gold", min=0, max=human.gold, skippable=True)

        waiter = ItemWaiter(ctx, prompt=ctx.translate("mail_item_prompt"), skippable=True)
        try:
            mail.item = await waiter.wait()
        except Skipped:
            pass

        if mail.item is not None:
            human_item, _ = HumanItem.get_or_create(item=mail.item, human=human)
            if human_item.amount < 1:
                raise SendableException(ctx.translate("item_not_found"))

            human_item.amount -= 1
            human_item.save()

        mail.residence = human.country
        mail.destination = recipient.country
        mail.end_date = mail.start_date + datetime.timedelta(minutes=mail.calculate_duration())
        human.gold -= mail.gold or 0
        sender.status = Pigeon.Status.mailing

        mail.save()
        human.save()
        sender.save()

        remind_emoji = "❗"
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Your pigeon is off to send a package to {recipient.mention}!"
        embed.set_footer(
            text=f"React with {remind_emoji} to get reminded when available.\n'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        message = await ctx.send(embed=embed)

        waiter = ReactionWaiter(ctx, message, emojis=(remind_emoji,), members=(ctx.author,))
        await waiter.add_reactions()
        emoji = await waiter.wait(remove=True)
        if emoji is not None:
            Reminder.create(
                user_id=ctx.author.id,
                channel_id=ctx.channel.id,
                message=ctx.translate("pigeon_ready_to_be_retrieved"),
                due_date=mail.end_date
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
                name=f"You've got mail from {mail.sender.human.user}!",
                icon_url=mail.sender.human.user.avatar_url
            )

            if mail.message is not None:
                embed.add_field(name="📜 message", value=mail.message, inline=False)
            if mail.gold > 0:
                embed.add_field(name=f"{GOLD_EMOJI} gold", value=f"{mail.gold}", inline=False)
            if mail.item is not None:
                lines = []
                lines.append(mail.item.name)
                if mail.item.usable:
                    lines.append(f"*{mail.item.description}*")
                embed.add_field(name="🎁 gift", value="\n".join(lines), inline=False)
                embed.set_thumbnail(url=mail.item.image_url)

            await ctx.send(embed=embed)

            mail.read = True
            mail.save()
            if mail.gold > 0:
                human.gold += mail.gold
                human.save()
            if mail.item is not None:
                human_item, _ = HumanItem.get_or_create(item=mail.item, human=mail.recipient)
                human_item.amount += 1
                human_item.save()

    @pigeon.command(name="stats")
    async def pigeon_stats(self, ctx, member: discord.Member = None):
        """Check the stats of your pigeon."""
        if member is not None:
            self.pigeon_check(ctx, member)

        member = member or ctx.author

        pigeon = ctx.pigeon
        embed = self.get_base_embed(ctx.guild)

        query = f"""
            SELECT COUNT(DISTINCT destination) as unique_countries_visited, COUNT(*) as total_countries_visited
            FROM legacy_exploration
            WHERE pigeon_id = {pigeon.id}
            AND finished = 1;
        """

        cursor = database.execute_sql(query)
        unique_countries_visited, total_countries_visited = cursor.fetchone()

        lines = []
        lines.append(f"Total explorations: {total_countries_visited}")
        lines.append(f"Unique countries visited: {unique_countries_visited}")

        embed.add_field(name=f"Explorations {Pigeon.Status.exploring.value}", value="\n".join(lines), inline=False)

        query = f"""
        SELECT SUM(gold) as total_gold_sent, count(id) as mails_sent
        FROM mail WHERE sender_id = {pigeon.id} AND finished = 1"""

        cursor = database.execute_sql(query)
        total_gold_sent, mails_sent = cursor.fetchone()

        lines = []
        lines.append(f"Total mails sent: {mails_sent}")
        lines.append(f"Total gold sent: {total_gold_sent}")
        embed.add_field(name=f"Mails {Pigeon.Status.mailing.value}", value="\n".join(lines), inline=False)

        win_condition = f"(pigeon1_id={ctx.pigeon.id} AND won=1) OR (pigeon2_id={ctx.pigeon.id} AND won=0)"

        query = f"""
SELECT
IFNULL(SUM(CASE WHEN ({win_condition}) THEN bet ELSE 0 END), 0) as gold_won,
IFNULL(SUM(CASE WHEN ({win_condition}) THEN 0 ELSE -bet END), 0) as gold_lost,
IFNULL(SUM(CASE WHEN ({win_condition}) THEN 1 ELSE 0 END), 0) as fights_won,
IFNULL(SUM(CASE WHEN ({win_condition}) THEN 0 ELSE 1 END), 0) as fights_lost
FROM fight
WHERE finished = 1
AND (pigeon1_id = {ctx.pigeon.id} OR pigeon2_id = {ctx.pigeon.id})
        """

        cursor = database.execute_sql(query)
        gold_won, gold_lost, fights_won, fights_lost = cursor.fetchone()
        profit = gold_won + gold_lost

        lines = []
        lines.append(f"Total fights won : {fights_won}")
        lines.append(f"Total fights lost: {fights_lost}")
        lines.append(f"Profit: {profit}")
        embed.add_field(name=f"Fights {Pigeon.Status.fighting.value}", value="\n".join(lines), inline=False)

        query = f"""
            SELECT
            IFNULL(SUM(CASE WHEN (accepted=1) THEN 1 ELSE 0 END), 0) as total_dates,
            IFNULL(SUM(CASE WHEN (pigeon2_id={ctx.pigeon.id} AND accepted=0) THEN 1 ELSE 0 END), 0) as total_rejections
            FROM date
            WHERE finished=1
            AND (pigeon1_id = {ctx.pigeon.id}  OR pigeon2_id = {ctx.pigeon.id} )
        """

        cursor = database.execute_sql(query)
        total_dates, rejections = cursor.fetchone()

        lines = []
        lines.append(f"Total dates: {total_dates}")
        lines.append(f"Rejections: {rejections}")
        embed.add_field(name=f"Dates {Pigeon.Status.dating.value}", value="\n".join(lines), inline=False)

        query = f"""SELECT in_possession, items_discovered, total_items FROM
            (SELECT COUNT(id) as items_discovered FROM human_item WHERE found = 1 AND human_id = {pigeon.human.id}) as hi1,
            (SELECT SUM(amount) AS in_possession FROM human_item WHERE human_id = {pigeon.human.id}) as hi2,
            (SELECT COUNT(id) AS total_items FROM item) as i1"""

        cursor = database.execute_sql(query)
        in_possession, items_discovered, total_items = cursor.fetchone()
        lines = []
        lines.append(f"Items discovered {items_discovered} / {total_items}")
        lines.append(f"Total items {in_possession}")

        embed.add_field(name=f"Human", value="\n".join(lines), inline=False)

        lines = []
        lines.append(f"Pooped on **{pigeon.poop_victim_count}** pigeons")
        lines.append(f"Been pooped on **{pigeon.pooped_on_count}** times")

        embed.add_field(name=f"Poop stats 💩", value="\n".join(lines), inline=False)

        asyncio.gather(ctx.send(embed=embed))

    @pigeon.command(name="history")
    async def pigeon_history(self, ctx, member: discord.Member = None):
        """Get the history of your or someone elses pigeon."""
        member = member or ctx.author
        query = Pigeon.select()
        query = query.where(Pigeon.human == ctx.get_human(user=member))
        query = query.where(Pigeon.condition != Pigeon.Condition.active)

        lines = []

        for pigeon in query:
            lines.append(pigeon.name)
        asyncio.gather(ctx.send("```\n{}```".format("\n".join(lines))))

    @pigeon.command(name="scoreboard")
    @commands.guild_only()
    async def pigeon_scoreboard(self, ctx):
        """View the scoreboard."""
        query = Pigeon.select(Pigeon.experience, Pigeon.name, Human.user_id)
        query = query.join(Human, on=(Pigeon.human == Human.id))
        query = query.join(Earthling, on=(Human.id == Earthling.human))
        query = query.where(Pigeon.condition == Pigeon.Condition.active)
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.order_by(Pigeon.experience.desc())

        table = Table(padding=0)
        table.add_row(Row(["rank", "exp", "pigeon", "owner"], header=True))

        i = 0
        for pigeon in query:
            user = pigeon.human.user
            if user is None:
                continue
            values = [f"{i + 1}", str(pigeon.experience), limit_str(pigeon.name, 10), limit_str(user, 10)]
            table.add_row(Row(values))
            i += 1

        await table.to_paginator(ctx, 15).wait()

    @pigeon.command(name="help")
    async def pigeon_help(self, ctx):
        embed = get_pigeon_tutorial_embed(ctx)
        paginator = Paginator.from_embed(ctx, embed, max_fields=10)
        await paginator.wait()

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
                        lines.append(
                            f"{pigeon.name} ellegantly and majestically enjoys {pigeon.gender.get_posessive_pronoun()} fry. (+10)")
                        score += 10
                    elif pigeon.food >= 30:
                        lines.append(
                            f"{pigeon.name} is clearly a bit hungry but still manages to (barely) not embarrass {pigeon.gender.get_pronoun(object=True)}self (+0)")
                    else:
                        lines.append(
                            f"{pigeon.name} is starving. As soon as {pigeon.gender.get_pronoun()} sees a fry {pigeon.gender.get_pronoun()} starts to drool, runs at it like a wild animal and devours it in one go. How unappealing. (-10)")
                        score -= 10

                    if pigeon.health <= 30:
                        lines.append(
                            f"{pigeon.name} is covered in blood. {pigeon.gender.get_pronoun()} tries to make it work but accidentally drips some blood on {other.name}s fry . Not a good sauce. (-10)")
                        score -= 10

                    if pigeon.happiness >= 60:
                        lines.append(f"{pigeon.name} smiled in confidence the entire date. (+10)")
                        score += 10
                    elif pigeon.happiness >= 30:
                        lines.append(
                            f"{pigeon.name} was clearly not in his best spirits. Slightly bringing his date down as well. (-5)")
                        score -= 5
                    else:
                        lines.append(
                            f"{pigeon.name} is miserable. From the start, {pigeon.gender.get_pronoun()} starts asking what the point of this date even is, what the point of anything is, and why {pigeon.gender.get_pronoun()} should even bother eating at all. (-10)")
                        score -= 10

                lines = "\n- " + ("\n\n- ".join(lines))
                embed.description = f"{lines}\n\nScore: **{score}**"
                embed.set_footer(text=f"{score // 10} relations")
                asyncio.gather(channel.send(embed=embed))

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

                winner_data = {"experience": 30, "health": -10}
                loser_data = {"experience": 5, "health": -25}

                embed.add_field(
                    name=f"💩 {loser.name} ({loser.human.user})",
                    value=get_winnings_value(**loser_data, gold=-fight.bet)
                )
                embed.add_field(
                    name=f"🏆 {winner.name} ({winner.human.user})",
                    value=get_winnings_value(**winner_data, gold=fight.bet)
                )

                asyncio.gather(channel.send(content=f"{winner.human.mention} | {loser.human.mention}", embed=embed))

                winner.status = Pigeon.Status.idle
                loser.status = Pigeon.Status.idle

                winner_data["gold"] = fight.bet * 2
                winner.update_stats(winner_data)
                loser.update_stats(loser_data)

                fight.won = won
                fight.finished = True
                fight.save()


def get_winnings_value(**kwargs):
    lines = []
    for key, value in kwargs.items():
        if value != 0:
            lines.append(f"{Pigeon.emojis[key]} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)


def get_active_pigeon(user, raise_on_none=False, human=None):
    try:
        return Pigeon.get(human=human or config.bot.get_human(user=user), condition=Pigeon.Condition.active)
    except Pigeon.DoesNotExist:
        return None


def pigeon_raise_if_not_exist(ctx, pigeon, name="pigeon"):
    if pigeon is None:
        ctx.command.reset_cooldown(ctx)
        raise SendableException(ctx.translate(f"{name}_does_not_exist"))


def pigeon_raise_if_unavailable(ctx, pigeon, name="pigeon"):
    pigeon_raise_if_not_exist(ctx, pigeon, name)
    if pigeon.status != Pigeon.Status.idle:
        ctx.command.reset_cooldown(ctx)
        raise SendableException(ctx.translate(f"{name}_not_idle").format(status=pigeon.status.name))


def pigeon_raise_if_stats_too_low(ctx, pigeon, name="pigeon"):
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
    raise SendableException(message.format(pigeon=pigeon))


def command_to_field(ctx, command, description=None):
    if isinstance(command, Cmd):
        desc = command.description
    else:
        desc = command.callback.__doc__

    kwargs = {}
    kwargs["value"] = f"`{ctx.prefix}{command.qualified_name}`"
    if description is None:
        kwargs["name"] = desc
    else:
        kwargs["value"] += f"\n{desc}{BR}"
    kwargs["inline"] = False
    return kwargs


class Cmd:
    __slots__ = ("name", "description")

    def __init__(self, name, description):
        self.name = name
        self.description = description

    @property
    def qualified_name(self):
        return "pigeon " + self.name


def get_rust_commands():
    return (
        Cmd("train", "Train your pigeon to get more gold"),
        Cmd("feed", "Feed your pigeon"),
        Cmd("clean", "Clean your pigeon"),
        Cmd("heal", "Heal your pigeon"),
        Cmd("play", "Play with your pigeon"),
        Cmd("poop", "Poop on other pigeons"),
        Cmd("explore", "Send your pigeon to other planets"),
        Cmd("space", "Perform actions on a planet"),
        Cmd("rob", "Steal from other pigeons"),
        Cmd("buy", "Get yourself a pigeon"),
    )


def get_pigeon_tutorial_embed(ctx):
    embed = discord.Embed(color=ctx.guild_color)
    lines = []

    for command in ctx.bot.get_command("pigeon").walk_commands():
        embed.add_field(**command_to_field(ctx, command))

    for command in get_rust_commands():
        embed.add_field(**command_to_field(ctx, command))

    embed.description = "\n".join(lines)
    return embed


async def setup(bot):
    await bot.add_cog(PigeonCog(bot))
