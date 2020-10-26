import random
import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Scene, Scenario, Human, Fight, Pigeon, Exploration, Mail, Settings, database
from src.discord.helpers.waiters import *
from src.games.game.base import DiscordIdentity
from src.discord.errors.base import SendableException

class PigeonCog(commands.Cog, name = "Pigeon"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.message_counts = {}

    def get_winnings_field(self, **kwargs):
        values = {"name" : "Winnings"}
        lines = []
        for key, value in kwargs.items():
            emoji = Pigeon.emojis[key]
            if value > 0:
                lines.append(f"{emoji} {key} +{value}")
            elif value < 0:
                lines.append(f"{emoji} {key} {value}")

        values["value"] = "\n".join(lines)
        return values

    def get_active_pigeon(self, user):
        try:
            return Pigeon.get(human = Human.get(user_id = user.id), dead = False)
        except Pigeon.DoesNotExist:
            raise SendableException("pigeon_not_found")

    def get_base_embed(self, guild):
        embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed

    def get_pigeon_channel(self, guild):
        with database:
            settings, _ = Settings.get_or_create(guild_id = guild.id)
        return settings.get_channel("pigeon")

    @commands.Cog.listener()
    async def on_ready(self):
        Pigeon.emojis["gold"] = self.bot.gold_emoji
        # self.poller.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.bot.production or message.guild is None:
            return

        guild = message.guild
        try:
            channel = self.get_pigeon_channel(guild)
        except SendableException:
            return

        if guild.id not in self.message_counts:
            self.message_counts[guild.id] = 0

        if message.channel.id == channel.id:
            self.message_counts[guild.id] += 1
            command = self.bot.command_prefix + "pigeon claim"
            if message.content == command:
                return

            likeliness = 4000
            if random.randint(self.message_counts[guild.id], likeliness) >= (likeliness-50):
                self.message_counts[guild.id] = 0
                embed = self.get_base_embed(message.guild)
                embed.title = "💩 Pigeon Droppings 💩"
                embed.description = f"Pigeon dropped something in chat! Type **{command}** it find out what it is."
                await message.channel.send(embed = embed)

                def check(m):
                    return m.content.lower() == command and m.channel.id == channel.id and not m.author.bot
                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60)
                except asyncio.TimeoutError:
                    embed = self.get_base_embed(message.guild)
                    embed.title = "💩 Pigeon Droppings 💩"
                    embed.description = f"The pigeon kept its droppings to itself."
                    await message.channel.send(embed = embed)
                else:
                    embed = self.get_base_embed(message.guild)
                    embed.title = "💩 Pigeon Droppings 💩"
                    money = random.randint(0, 100)
                    embed.description = f"{msg.author.mention}, you picked up the droppings and received {self.bot.gold_emoji} {money}"
                    await message.channel.send(embed = embed)
                    identity = DiscordIdentity(msg.author)
                    identity.add_points(money)

    @commands.group()
    async def pigeon(self, ctx):
        pass

    @pigeon.command(name = "buy")
    async def pigeon_buy(self, ctx):
        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
            pigeon = human.pigeons.select(Pigeon.dead == False).first()

            if pigeon is not None:
                asyncio.gather(ctx.send(ctx.translate("pigeon_already_purchased").format(name = pigeon.name)))
                return

            prompt = lambda x : ctx.translate(f"pigeon_{x}_prompt")

            pigeon = Pigeon(human = human)
            waiter = StrWaiter(ctx, prompt = prompt("name"), max_words = None)
            pigeon.name = await waiter.wait()
            pigeon.save()

            pigeon_price = 50
            identity = DiscordIdentity(ctx.author)
            identity.remove_points(pigeon_price)

            embed = self.get_base_embed(ctx.guild)
            embed.set_footer(text = f"-{pigeon_price}")
            embed.description = ctx.translate("pigeon_purchased")
            asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "challenge", aliases = ["fight"])
    async def pigeon_challenge(self, ctx, member : discord.Member):
        channel = self.get_pigeon_channel(ctx.guild)

        with database:
            challenger = self.get_active_pigeon(ctx.author)
            challengee = self.get_active_pigeon(member.id)

            if challenger is None:
                raise SendableException(ctx.translate("you_no_pigeon"))
            if challengee is None:
                raise SendableException(ctx.translate("challengee_no_pigeon"))

            if challenger.status != Pigeon.Status.idle:
                raise SendableException(ctx.translate("challenger_not_idle"))

            if challengee.status != Pigeon.Status.idle:
                raise SendableException(ctx.translate("challengee_not_idle"))

            fight = Fight(guild_id = ctx.guild.id)
            fight.challenger = challenger
            fight.challengee = challengee
            fight.save()

            for pigeon in (challenger, challengee):
                pigeon.status = Pigeon.Status.fight
                pigeon.save()

        embed = self.get_base_embed(ctx.guild)
        embed.title = "Pigeon Challenge"
        embed.description = f"{challenger.name} has challenged {challengee.name} to a pigeon fight."
        embed.set_footer(text = f"use '{ctx.prefix}pigeon accept' to accept") 
        asyncio.gather(channel.send(embed = embed))

    @pigeon.command(name = "accept")
    async def pigeon_accept(self, ctx):
        with database:
            challenge = self.get_active_pigeon(ctx.author)

            query = Fight.select()
            query = query.where(Fight.finished == False)
            query = query.where(Fight.challengee == challengee)
            fight = query.first()

            if fight is None:
                raise SendableException(ctx.translate("no_challenger"))

            fight.accepted = True
            fight.start_date = datetime.datetime.utcnow() + datetime.timedelta(hours = 1)
            fight.start_date = datetime.datetime.utcnow() + datetime.timedelta(minutes = 5)

            fight.save()

            embed = self.get_base_embed(ctx.guild)
            embed.description = f"{ctx.author.mention} has accepted the challenge!"
            embed.set_footer(text = "Fight will start at")
            embed.timestamp = fight.start_date

            channel = self.get_pigeon_channel(ctx.guild)

            await channel.send(embed = embed)

    @pigeon.command(name = "explore")
    async def pigeon_explore(self, ctx):
        with database:
            pigeon = self.get_active_pigeon(ctx.author)
            if pigeon.status != Pigeon.Status.idle:
                raise SendableException(ctx.translate("pigeon_not_idle").format(status = pigeon.status.name))

            def get_random_country():
                country_code = None
                countries = list(pycountry.countries)
                while country_code is None:
                    country_code = random.choice(countries).alpha_2
                    try:
                        CountryInfo(country_code).capital()
                    except KeyError:
                        country_code = None

                return country_code

            residence = pigeon.human.country_code or get_random_country()
            destination = get_random_country()

            exploration = Exploration(
                residence = residence,
                destination = destination,
                pigeon = pigeon
            )

            current_date = datetime.datetime.utcnow()

            min_time_in_minutes = 30
            max_time_in_minutes = 180
            km = int(exploration.distance_in_km)
            duration = int(km / 40)
            if duration < min_time_in_minutes:
                duration = min_time_in_minutes
            elif duration > max_time_in_minutes:
                duration = max_time_in_minutes

            exploration.end_date = exploration.start_date + datetime.timedelta(minutes = duration)
            pigeon.status = Pigeon.Status.exploring
            pigeon.save()
            exploration.save()

            embed = self.get_base_embed(ctx.guild)
            embed.description = "Okay. Your pigeon is now off to explore a random location!"
            embed.set_footer(text = f"'{ctx.prefix}pigeon retrieve' to check on your pigeon")
            asyncio.gather(ctx.send(embed = embed))

    @pigeon.command(name = "retrieve")
    async def pigeon_retrieve(self, ctx):
        with database:
            pigeon = self.get_active_pigeon(ctx.author)
            if pigeon.status == Pigeon.Status.idle:
                raise SendableException(ctx.translate("pigeon_idle"))

            embed = self.get_base_embed(ctx.guild)

            activity = pigeon.current_activity

            if activity is None:
                raise SendableException(ctx.translate("nothing_to_retrieve"))

            if isinstance(activity, Exploration):
                if activity.end_date_passed:
                    country_name = pycountry.countries.get(alpha_2 = activity.destination).name

                    text = f"{pigeon.name} soared through the skies for **{activity.duration_in_minutes}** minutes"
                    text += f" over a distance of **{int(activity.distance_in_km)}** Kilometers"
                    text += f" until it finally reached **{country_name}**"

                    multiplier = 1
                    if random.randint(1,10) == 1:
                        multiplier = 2
                        text += " it even picked up some of the local language!"

                    embed.description = text

                    winnings = {
                        "gold"        : int(activity.gold_worth * multiplier),
                        "experience"  : int(activity.xp_worth * multiplier),
                        "food"        : -random.randint(10,40),
                        "happiness"   : int(random.randint(10,40) * multiplier),
                        "cleanliness" : -random.randint(10,40),
                        "food"        : -random.randint(10, 40)
                    }

                    embed.add_field(**self.get_winnings_field(**winnings))

                    for key, value in winnings.items():
                        if key == "gold":
                            pigeon.human.gold += value
                        else:
                            setattr(pigeon, key, (getattr(pigeon, key) + value) )

                    activity.finished = True
                    pigeon.status = Pigeon.Status.idle
                    pigeon.human.save()
                    pigeon.save()
                    activity.save()
                else:
                    embed.description = f"**{pigeon.name}** is still on its way to explore!"
                    embed.set_footer(text = "Check back at", icon_url = "https://www.animatedimages.org/data/media/678/animated-pigeon-image-0045.gif")
                    embed.timestamp = activity.end_date
                await ctx.send(embed = embed)

            elif isinstance(activity, Mail):
                print("mail activity")

    @pigeon.command(name = "mail")
    async def pigeon_mail(self, ctx, user : discord.User):
        pass



    # @tasks.loop(seconds=30)
    # async def fight_ticker(self):
    #     with database:
    #         query = Fight.select()
    #         query = query.where(Fight.ended == False)
    #         query = query.where(Fight.accepted == True)
    #         query = query.where(Fight.start_date <= datetime.datetime.utcnow())
    #         for fight in query:
    #             won = random.randint(0, 1) == 0
    #             guild = fight.guild
    #             channel = self.get_pigeon_channel(guild)

    #             if won:
    #                 winner = fight.challenger
    #                 loser = fight.challengee
    #             else:
    #                 winner = fight.challengee
    #                 loser = fight.challenger

    #             embed = self.get_base_embed(guild)
    #             embed.title = f"{fight.challenger.pigeon.name} vs {fight.challengee.pigeon.name}"

    #             bet = 50
    #             embed.description = f"{winner.mention}s pigeon destroys {loser.mention}s pigeon. Winner takes {self.bot.gold_emoji} {bet} from the losers wallet"
    #             asyncio.gather(channel.send(embed = embed))
    #             winner.gold += bet
    #             loser.gold -= bet
    #             winner.save()
    #             loser.save()

    #             loser.pigeon.delete_instance()

    #             fight.won = won
    #             fight.ended = True
    #             fight.save()

def setup(bot):
    bot.add_cog(PigeonCog(bot))