import random
import asyncio

import discord
from discord.ext import commands, tasks

import src.config as config
from src.models import Scene, Scenario, GlobalHuman, Fight, Pigeon, Bet, database
from src.discord.helpers.waiters import *
from src.games.game.base import DiscordIdentity
from src.discord.errors.base import SendableException

class PigeonCog(commands.Cog, name = "Pigeon"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.message_counts = {}

    guilds = \
    {
        742146159711092757: 742163352712642600,
        761624318291476482:766643537269751849
    }

    def get_base_embed(self, guild):
        embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705242963550404658/766680730457604126/pigeon_tiny.png")
        return embed

    def get_pigeon_channel(self, guild):
        return guild.get_channel(self.guilds[guild.id])

    @commands.Cog.listener()
    async def on_ready(self):
        self.poller.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.bot.production:
            return

        guild = message.guild
        if guild.id not in self.guilds:
            return
        if guild.id not in self.message_counts:
            self.message_counts[guild.id] = 0

        channel = self.get_pigeon_channel(guild)

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

    async def perform_scenario(self, ctx):
        with database:
            identity = DiscordIdentity(ctx.author)
            scene = Scene.get(command_name = ctx.command.name, group_name = ctx.root_parent.name)
            await scene.send(ctx, identity = identity)

    @pigeon.command(name = "help")
    async def pigeon_help(self, ctx):
        embed_data = {
            "title": "⋆ Broken Pigeon-Phone ⋆",
            "description": "**__Money Generator__**\n• /pigeon feed\n• /pigeon chase\n• /pigeon yell\n• /pigeon fish\n\n**__Interactive__**\n• /pigeon claim: Droppings spawn randomly. Input claim to collect it.\n• /pigeon buy: Purchase a pigeon for Pigeon Fight.\n• /pigeon fight: \n",
            "footer": {
                "text": "There is a 4h cooldown for all Money Generator commands.",
                "icon_url": "https://cdn.discordapp.com/attachments/705242963550404658/766661638224216114/pigeon.png"
            }
        }

        embed = discord.Embed.from_dict(embed_data)
        embed.color = ctx.guild_color
        asyncio.gather(ctx.send(embed = embed))

    # @commands.command()
    # async def wot(self, ctx):
    #     waiter = StrWaiter(ctx, prompt = f"type some shit", max_words = None)
    #     value = await waiter.wait()
    #     asyncio.gather(ctx.send("OK"))

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "feed")
    async def pigeon_feed(self, ctx):
        asyncio.gather(self.perform_scenario(ctx))

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "yell")
    async def pigeon_yell(self, ctx):
        asyncio.gather(self.perform_scenario(ctx))

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "chase")
    async def pigeon_chase(self, ctx):
        asyncio.gather(self.perform_scenario(ctx))

    @commands.cooldown(1, (3600 * 4), type=commands.BucketType.user)
    @pigeon.command(name = "fish")
    async def pigeon_fish(self, ctx):
        asyncio.gather(self.perform_scenario(ctx))

    @pigeon.command(name = "buy")
    async def pigeon_buy(self, ctx):
        with database:
            global_human, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)
            pigeon = global_human.pigeon
            if pigeon is not None:
                # raise SendableException("pigeon_ale")
                asyncio.gather(ctx.send(f"You already have a lovely pigeon named **{pigeon.name}**!"))
                return

            prompt = lambda x : ctx.translate(f"pigeon_{x}_prompt")

            pigeon = Pigeon(global_human = global_human)
            waiter = StrWaiter(ctx, prompt = prompt("name"), max_words = None)
            pigeon.name = await waiter.wait()
            pigeon.save()

            pigeon_price = 50
            identity = DiscordIdentity(ctx.author)
            identity.remove_points(pigeon_price)
            asyncio.gather(ctx.send(ctx.translate("pigeon_purchased")))

    @pigeon.command(name = "challenge")
    async def pigeon_challenge(self, ctx, member : discord.Member):
        with database:
            challenger, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)
            challengee, _ = GlobalHuman.get_or_create(user_id = member.id)

            if challenger.pigeon is None:
                raise SendableException(ctx.translate("you_no_pigeon"))
            if challengee.pigeon is None:
                raise SendableException(ctx.translate("challengee_no_pigeon"))

            query = Fight.select()
            query = query.where( Fight.ended == False )
            query = query.where( (Fight.challenger == challenger) | (Fight.challengee == challenger) | (Fight.challenger == challengee) | (Fight.challengee == challengee) )
            pending_challenge = query.first()
            if pending_challenge is not None:
                raise SendableException(ctx.translate("already_fight_pending"))

            fight = Fight(guild_id = ctx.guild.id)
            fight.challenger = challenger
            fight.challengee = challengee
            fight.save()

        channel = self.get_pigeon_channel(ctx.guild)
        await channel.send(f"{challenger.mention} has challenged {challengee.mention} to a pigeon fight.")

    @pigeon.command(name = "accept")
    async def pigeon_accept(self, ctx):
        with database:
            challengee, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)

            query = Fight.select()
            query = query.where(Fight.ended == False)
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

    @pigeon.command(name = "bet")
    async def pigeon_bet(self, ctx, member : discord.Member):
        with database:
            global_human, _ = GlobalHuman.get_or_create(user_id = member.id)

            query = Fight.select()
            query = query.where( Fight.ended == False )
            query = query.where( (Fight.challenger == global_human) | (Fight.challengee == global_human))
            fight = query.first()

            if fight is None:
                raise SendableException(ctx.translate("no_fight_found"))

            if fight.challengee.user_id == ctx.author.id or fight.challenger.user_id == ctx.author.id:
                raise SendableException(ctx.translate("cannot_vote_own_fight"))

            Bet.create(fight = fight, global_human = global_human)
            asyncio.gather(ctx.send(ctx.translate("bet_created")))


    @tasks.loop(minutes=1)
    async def poller(self):
        with database:
            query = Fight.select()
            query = query.where(Fight.ended == False)
            # query = query.where(Fight.start_date <= datetime.datetime.utcnow())
            for fight in query:
                if not fight.start_date_passed:
                    continue

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
                embed.title = f"{fight.challenger.pigeon.name} vs {fight.challengee.pigeon.name}"

                bet = 50
                embed.description = f"{winner.mention}s pigeon destroys {loser.mention}s pigeon. Winner takes {self.bot.gold_emoji} {bet} from the losers wallet"
                asyncio.gather(channel.send(embed = embed))
                winner.gold += bet
                loser.gold -= bet
                winner.save()
                loser.save()

                loser.pigeon.delete_instance()

                fight.won = won
                fight.ended = True
                fight.save()



def setup(bot):
    bot.add_cog(PigeonCog(bot))