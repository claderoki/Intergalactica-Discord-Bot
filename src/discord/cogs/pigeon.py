import random
import asyncio

import discord
from discord.ext import commands, tasks
from countryinfo import CountryInfo

import src.config as config
from src.models import Scene, Scenario, Human, Fight, Pigeon, Earthling, Item, Exploration, Mail, Settings, SystemMessage, database
from src.models.base import PercentageField
from src.discord.helpers.waiters import *
from src.utils.country import Country
from src.games.game.base import DiscordIdentity
from src.discord.errors.base import SendableException
from src.discord.helpers.pretty import prettify_dict, Table, Row
from src.discord.helpers.exploration_retrieval import ExplorationRetrieval, MailRetrieval
from src.utils.enums import Gender
from src.discord.helpers.converters import EnumConverter

class PigeonCog(commands.Cog, name = "Pigeon"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
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
        if self.bot.production:
            self.fight_ticker.start()
        else:
            await asyncio.sleep(60 * 60)
            self.stats_ticker.start()

    @commands.group()
    async def pigeon(self, ctx):
        human, _ = Human.get_or_create(user_id = ctx.author.id)
        for message in list(human.system_messages.where(SystemMessage.read == False)):
            await ctx.send(embed = message.embed)
            message.read = True
            message.save()

        subcommands_no_require_pigeon = ["buy", "scoreboard", "help"]
        subcommands_no_require_available = ["status", "stats", "languages", "retrieve", "gender", "name"] + subcommands_no_require_pigeon
        subcommands_no_require_stats = ["heal", "clean", "feed", "play"] + subcommands_no_require_available

        subcommand = ctx.invoked_subcommand.name

        if subcommand not in subcommands_no_require_pigeon:
            ctx.pigeon = get_active_pigeon(ctx.author)
            pigeon_raise_if_not_exist(ctx, ctx.pigeon)
        if subcommand not in subcommands_no_require_available:
            pigeon_raise_if_unavailable(ctx, ctx.pigeon)
        if subcommand not in subcommands_no_require_stats:
            pigeon_raise_if_stats_too_low(ctx, ctx.pigeon)

    @pigeon.command(name = "buy")
    async def pigeon_buy(self, ctx):
        """Buy a pigeon."""

        pigeon = get_active_pigeon(ctx.author)

        if pigeon is not None:
            asyncio.gather(ctx.send(ctx.translate("pigeon_already_purchased").format(name = pigeon.name)))
            return

        prompt = lambda x : ctx.translate(f"pigeon_{x}_prompt")

        pigeon = Pigeon(human = Human.get(user_id = ctx.author.id))
        waiter = StrWaiter(ctx, prompt = prompt("name"), max_words = None)
        pigeon.name = await waiter.wait()
        pigeon.save()

        cost = 50
        pigeon.human.gold -= cost
        pigeon.human.save()

        embed = self.get_base_embed(ctx.guild)
        embed.description = ctx.translate("pigeon_purchased") + "\n" + get_winnings_value(gold = -cost)
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "challenge", aliases = ["fight"])
    async def pigeon_challenge(self, ctx, member : discord.Member):
        """Challenge another user to a fight."""

        channel = self.get_pigeon_channel(ctx.guild)
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_challenge_self"))

        challenger = ctx.pigeon

        challengee = get_active_pigeon(member)
        pigeon_raise_if_stats_too_low(ctx, challenger, name = "challenger")
        pigeon_raise_if_stats_too_low(ctx, challengee, name = "challengee")

        fight = Fight(guild_id = ctx.guild.id, start_date = None)

        prompt = lambda x : ctx.translate(f"fight_{x}_prompt")
        waiter = IntWaiter(ctx, prompt = prompt("bet"), min = 0, max = min([challenger.human.gold, challengee.human.gold]), skippable = True)
        try:
            fight.bet = await waiter.wait()
        except Skipped:
            pass

        if challenger.human.gold < fight.bet:
            raise SendableException(ctx.translate("challenger_not_enough_gold").format(bet = fight.bet))
        if challengee.human.gold < fight.bet:
            raise SendableException(ctx.translate("challengee_not_enough_gold").format(bet = fight.bet))

        fight.challenger = challenger
        fight.challengee = challengee
        fight.save()

        for pigeon in (challenger, challengee):
            pigeon.status = Pigeon.Status.fighting
            pigeon.save()

        embed = self.get_base_embed(ctx.guild)
        embed.title = "Pigeon Challenge"
        embed.description = f"{challenger.name} has challenged {challengee.name} to a pigeon fight.\nThe stake for this fight is `{fight.bet}`"
        embed.set_footer(text = f"use '{ctx.prefix}pigeon accept' to accept") 
        asyncio.gather(channel.send(embed = embed))


    @pigeon.command(name = "languages", aliases = ["lang"])
    async def pigeon_languages(self, ctx):
        lines = []
        for language_mastery in ctx.pigeon.language_masteries:
            lines.append(f"{language_mastery.language.name} - {language_mastery.mastery}%")
        if len(lines):
            asyncio.gather(ctx.send("\n".join(lines)))
        else:
            asyncio.gather(ctx.send("No languages yet."))


    @pigeon.command(name = "gender")
    async def pigeon_gender(self, ctx, gender : EnumConverter(Gender)):
        ctx.pigeon.gender = gender
        ctx.pigeon.save()
        asyncio.gather(ctx.send(ctx.translate("gender_set").format(gender = gender.name)))

    @pigeon.command(name = "name")
    async def pigeon_name(self, ctx, *, name : str):
        cost = 50
        raise_if_not_enough_gold(ctx, cost, ctx.pigeon.human)
        ctx.pigeon.name = name
        ctx.pigeon.save()
        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Name has been set to {name}" + "\n" + get_winnings_value(gold = -cost)
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "accept")
    async def pigeon_accept(self, ctx):
        """Accept a pending fight."""

        challengee = ctx.pigeon

        query = Fight.select()
        query = query.where(Fight.finished == False)
        query = query.where(Fight.challengee == challengee)
        fight = query.first()

        if fight is None:
            raise SendableException(ctx.translate("no_challenger"))

        error = None
        if fight.challenger.human.gold < fight.bet:
            error = ctx.translate("challenger_not_enough_gold").format(bet = fight.bet)
        if fight.challengee.human.gold < fight.bet:
            error = ctx.translate("challengee_not_enough_gold").format(bet = fight.bet)
        if error is not None:
            for pigeon in (challenger, challengee):
                pigeon.status = Pigeon.Status.idle
                pigeon.save()
            fight.delete_instance()
            raise SendableException(error)

        fight.accepted = True
        fight.start_date = datetime.datetime.utcnow() + datetime.timedelta(minutes = 5)

        for human in (fight.challenger.human, fight.challengee.human):
            human.gold -= fight.bet
            human.save()

        fight.save()

        embed = self.get_base_embed(ctx.guild)
        embed.description = f"{ctx.author.mention} has accepted the challenge!"
        embed.set_footer(text = "Fight will start at")
        embed.timestamp = fight.start_date

        channel = self.get_pigeon_channel(ctx.guild)

        await channel.send(embed = embed)

    @pigeon.command(name = "explore")
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

        embed = self.get_base_embed(ctx.guild)
        embed.description = "Okay. Your pigeon is now off to explore a random location!"
        embed.set_footer(text = f"'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "retrieve", aliases = ["return"] )
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
                retrieval.commit()
                return await ctx.send(embed = retrieval.embed)
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to explore!"
                embed.set_footer(text = "Check back at", icon_url = "https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date
        elif isinstance(activity, Mail):
            if activity.end_date_passed:
                retrieval = MailRetrieval(activity)
                retrieval.commit()
                return await ctx.send(embed = retrieval.embed)
            else:
                embed.description = f"**{pigeon.name}** is still on {pigeon.gender.get_posessive_pronoun()} way to send a message!"
                embed.set_footer(text = "Check back at", icon_url = "https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                embed.timestamp = activity.end_date

        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "mail", aliases = ["message", "send", "letter"])
    async def pigeon_mail(self, ctx, user : discord.User):
        """Send someone a pigeon letter."""
        if user.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_send_to_self"))

        sender = ctx.pigeon

        ctx.channel = ctx.author.dm_channel
        if ctx.channel is None:
            ctx.channel = await ctx.author.create_dm()

        recipient, _ = Human.get_or_create(user_id = user.id)

        mail = Mail(recipient = recipient, sender = sender, read = False)

        await mail.editor_for("message", ctx)
        await mail.editor_for("gold", ctx, min = 0, max = sender.human.gold, skippable = True)

        mail.residence   = sender.human.country
        mail.destination = recipient.country
        mail.end_date = mail.start_date + datetime.timedelta(minutes = mail.calculate_duration())
        sender.human.gold -= mail.gold
        sender.status = Pigeon.Status.mailing

        mail.save()
        sender.human.save()
        sender.save()

        embed = self.get_base_embed(ctx.guild)
        embed.description = f"Okay. Your pigeon is off to send a package to {recipient.mention}!"
        embed.set_footer(text = f"'{ctx.prefix}pigeon retrieve' to check on your pigeon")
        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "inbox")
    async def pigeon_inbox(self, ctx):
        """Check your inbox."""
        human, _ = Human.get_or_create(user_id = ctx.author.id)
        unread_mail = human.inbox.where(Mail.read == False).where(Mail.finished == True)
        if len(unread_mail) == 0:
            return await ctx.send(ctx.translate("no_unread_mail"))

        for mail in list(unread_mail):
            embed = self.get_base_embed(ctx.guild)
            if mail.gold > 0:
                embed.description = f"{mail.sender.human.mention} has sent you some gold ({mail.gold}) with a message attached:\n`{mail.message}`"
            else:
                embed.description = f"{mail.sender.human.mention} has sent you a message:\n`{mail.message}`"

            await ctx.send(embed = embed)

            mail.read = True
            mail.recipient.gold += mail.gold
            mail.save()
            mail.recipient.save()

    @pigeon.command(name = "stats")
    async def pigeon_stats(self, ctx, member : discord.Member = None):
        member = member or ctx.author
        pigeon = ctx.pigeon
        embed = self.get_base_embed(ctx.guild)

        explorations = pigeon.explorations.where(Exploration.finished == True)
        unique_countries_visited = {x.destination.alpha_2 for x in explorations}

        lines = []
        lines.append(f"Total explorations: {len(explorations)}")
        lines.append(f"Unique countries visited: {len(unique_countries_visited)}")
        embed.add_field(name = f"Explorations {Pigeon.Status.exploring.value}", value = "\n".join(lines), inline = False)

        mails = pigeon.outbox.where(Mail.finished == True)
        total_gold_sent = sum([x.gold for x in mails if x.gold is not None])

        lines = []
        lines.append(f"Total mails sent: {len(mails)}")
        lines.append(f"Total gold sent: {total_gold_sent}")
        embed.add_field(name = f"Mails {Pigeon.Status.mailing.value}", value = "\n".join(lines), inline = False)

        fights = pigeon.fights.where(Fight.finished == True)
        fights_won = 0
        fights_lost = 0
        profit = 0
        for fight in fights:
            if fight.challenger == pigeon and fight.won:
                fights_won += 1
                profit += fight.bet
            elif fight.challengee == pigeon and not fight.won:
                fights_won += 1
                profit += fight.bet
            else:
                fights_lost += 1
                profit -= fight.bet

        lines = []
        lines.append(f"Total fights won : {fights_won}")
        lines.append(f"Total fights lost: {fights_lost}")
        lines.append(f"Profit: {profit}")
        embed.add_field(name = f"Fights {Pigeon.Status.fighting.value}", value = "\n".join(lines), inline = False)

        asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "status")
    async def pigeon_status(self, ctx, member : discord.Member = None):
        """Check the status of your pigeon."""
        member = member or ctx.author
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
        asyncio.gather(ctx.send(embed = embed))

    def increase_stats(self, ctx, attr_name, attr_increase, cost, message):
        pigeon = ctx.pigeon

        value = getattr(pigeon, attr_name)
        if value == 100:
            raise SendableException(ctx.translate(f"{attr_name}_already_max"))

        pigeon.human.gold  -= cost
        setattr(pigeon, attr_name, value+attr_increase )
        pigeon.human.save()
        pigeon.save()

        embed = self.get_base_embed(ctx.guild )
        embed.description = message.format(pigeon = pigeon)
        embed.description += get_winnings_value(**{attr_name : attr_increase, 'gold' : -cost})
        asyncio.gather(ctx.send(embed = embed))

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @pigeon.command(name = "clean")
    async def pigeon_clean(self, ctx):
        self.increase_stats(ctx, 'cleanliness', 20, 15, "You happily clean up **{pigeon.name}s** fecal matter.\n")

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @pigeon.command(name = "feed")
    async def pigeon_feed(self, ctx):
        self.increase_stats(ctx, 'food', 20, 15, "You feed **{pigeon.name}** some seeds and whatever else they eat.\n")

    @pigeon.command(name = "scoreboard")
    async def pigeon_scoreboard(self, ctx):
        query = Pigeon.select()
        query = query.join(Human, on = (Pigeon.human == Human.id) )
        query = query.join(Earthling, on = (Human.id == Earthling.human) )
        query = query.where(Pigeon.condition == Pigeon.Condition.active)
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.order_by(Pigeon.experience.desc())

        embed = discord.Embed(title = "Scoreboard")

        rows = []
        rows.append(Row(["rank", "exp", "pigeon"], header = True))

        top = 1
        i = (top-1)
        for pigeon in query:
            values = [f"{i+1}", str(pigeon.experience), str(pigeon.name)]
            rows.append(Row(values))
            if len(rows) == 10:
                break
            i += 1

        table = Table(rows)
        embed.description = table.generate()
        await ctx.send(embed = embed)

    @commands.cooldown(1, (3600 * 1), type=commands.BucketType.user)
    @pigeon.command(name = "heal")
    async def pigeon_heal(self, ctx):
        self.increase_stats(ctx, 'health', 20, 15, "You give **{pigeon.name}** some seed you found inside your couch and convince it of its healing effects.\n")

    @pigeon.command(name = "help")
    async def pigeon_help(self, ctx):
        await ctx.send_help(ctx.command.root_parent)

    @tasks.loop(seconds=30)
    async def fight_ticker(self):
        query = Fight.select()
        query = query.where(Fight.finished == False)
        query = query.where(Fight.accepted == True)
        query = query.where(Fight.start_date <= datetime.datetime.utcnow())
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
            embed.title = f"{winner.name} creeps into {loser.name}’s room. {winner.name}’s jaw unhinges and swallows {loser.name} whole."

            winner_data = {"experience" : 30, "health" : -10}
            loser_data = {"experience" : 5, "health" : -25}

            embed.add_field(name = f"💩 {loser.name}", value = get_winnings_value(**loser_data, gold = -fight.bet))
            embed.add_field(name = f"🏆 {winner.name}", value = get_winnings_value(**winner_data, gold = fight.bet))

            asyncio.gather(channel.send(embed = embed))

            pigeon.update_stats(winner_data)
            pigeon.update_stats(loser_data)

            winner.human.gold += (fight.bet*2)

            winner.status = Pigeon.Status.idle
            loser.status = Pigeon.Status.idle

            winner.save()
            winner.human.save()
            loser.save()

            fight.won = won
            fight.finished = True
            fight.save()

    @tasks.loop(hours = 1)
    async def stats_ticker(self):
        with database.connection_context():
            for pigeon in Pigeon.select().where(Pigeon.condition == Pigeon.Condition.active).where(Pigeon.status == Pigeon.Status.idle):
                data = {"food": -1, "cleanliness" : -1, "happiness": -1}
                if pigeon.food <= 20 or pigeon.cleanliness <= 20:
                    data["health"] = -1
                if pigeon.food == 0:
                    data["health"] = -2

                print(data)
                pigeon.update_stats(data)
                pigeon.save()

def get_winnings_value(**kwargs):
    lines = []
    for key, value in kwargs.items():
        lines.append(f"{Pigeon.emojis[key]} {'+' if value > 0 else ''}{value}")
    return ", ".join(lines)

def get_active_pigeon(user, raise_on_none = False):
    try:
        return Pigeon.get(human = Human.get(user_id = user.id), condition = Pigeon.Condition.active)
    except Pigeon.DoesNotExist:
        return None

def pigeon_raise_if_not_exist(ctx, pigeon, name = "pigeon"):
    if pigeon is None:
        raise SendableException(ctx.translate(f"{name}_does_not_exist"))

def pigeon_raise_if_unavailable(ctx, pigeon, name = "pigeon"):
    pigeon_raise_if_not_exist(ctx, pigeon, name)
    if pigeon.status != Pigeon.Status.idle:
        raise SendableException(ctx.translate(f"{name}_not_idle").format(status = pigeon.status.name))

def pigeon_raise_if_stats_too_low(ctx, pigeon, name = "pigeon"):
    if pigeon.cleanliness <= 10:
        raise SendableException(ctx.translate(f"{name}_too_stinky"))
    if pigeon.happiness <= 10:
        raise SendableException(ctx.translate(f"{name}_too_sad"))
    if pigeon.food <= 10:
        raise SendableException(ctx.translate(f"{name}_too_hungry"))
    if pigeon.health <= 10:
        raise SendableException(ctx.translate(f"{name}_too_wounded"))

def raise_if_not_enough_gold(ctx, gold, human, name = "you"):
    if human.gold < gold:
        raise SendableException(ctx.translate(f"{name}_not_enough_gold"))

def setup(bot):
    bot.add_cog(PigeonCog(bot))