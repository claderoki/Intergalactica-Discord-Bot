import asyncio
import datetime
import random

import discord
from discord.ext import commands, tasks

from src.models import Game, Player, Settings, KillMessage, database
from src.discord.errors.assassins import NotSetup, GameRunning




def is_setup():
    def predicate(ctx):
        return True
        try:
            Settings.get(guild_id = ctx.guild.id)
        except Settings.DoesNotExist:
            raise NotSetup(f"To begin, setup a log channel first. `{ctx.prefix}logchannel #channel`")
        else:
            return True

    return commands.check(predicate)

class AssassinsCog(commands.Cog, name = "Assassins"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.poll.start()

    # @commands.command()
    # async def test(self, ctx):
    #     await self.choose_game(ctx.author)

    async def choose_game(self, member):
        mutual_guilds = [x.id for x in self.bot.guilds if x.get_member(member.id) is not None]

        games = list(Game.select().where( (Game.guild_id.in_(mutual_guilds)) & ( Game.active == True) ))

        if len(games) == 1:
            return games[0]

    @commands.command()
    async def msg(self, ctx):
        kill_message = KillMessage.get_random().value.format(user = ctx.author)
        await ctx.send(embed = discord.Embed(title = kill_message))

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     if message.channel.id != 710402878652809276:
    #         return

    #     if "{user}" in message.content:
    #         KillMessage.create(value = message.content.strip("`"))
    #         await message.add_reaction("☑️")

    @commands.group()
    async def assassins(self, ctx):
        pass

    @commands.max_concurrency(1, commands.BucketType.guild)
    @assassins.command()
    async def start(self, ctx, minutes_to_start : float = 30):
        game = Game.create(guild_id = ctx.guild.id)

        join_emoji = "⬆️"

        message = await game.log(f"React with an {join_emoji} to join. In {minutes_to_start} minutes the game will start.")
        await message.add_reaction(join_emoji)

        await asyncio.sleep(minutes_to_start * 60)

        message = await message.channel.fetch_message(message.id)

        join_reaction = None

        for reaction in message.reactions:
            if str(reaction.emoji) == join_emoji:
                join_reaction = reaction
                break

        members = [x for x in await join_reaction.users().flatten() if not x.bot]
        random.shuffle(members)


        if len(members) < 1:
            await message.edit(content = "Not enough players")
            game.delete_instance()
            return

        players = []
        for member in members:
            players.append(Player.create(user_id = member.id, game = game))

        game.start()

    @commands.dm_only()
    @assassins.command()
    async def kill(self, ctx, code : str):
        game = await self.choose_game(ctx.author)
        if game is None:
            return await ctx.send("No game running for you.")

        player = Player.get(game = game, user_id = ctx.author.id, alive = True)

        if not player.kill_command_available:
            return await ctx.send("You have already used your kill this cycle.")

        target = player.target

        if target.code == code:

            target.alive = False
            target.save()

            player.kills += 1
            player.target = target.target

            player.save()

            if game.ended:
                await ctx.send(embed = discord.Embed(title = "🎯 Assassination successful."))
                game.end()
            elif game.new_round_available:
                await ctx.send(embed = discord.Embed(title = "🎯 Assassination successful."))
                game.next_round()
            else:
                await ctx.send(embed = discord.Embed(title = f"Assassination successful. 🎯 New target: {target.target.member}"))

            kill_message = KillMessage.get_random().value.format(user = target.member)
            await game.log(embed = discord.Embed(title = kill_message))

        else:
            player.kill_command_available = False
            player.save()
            await ctx.send(embed = discord.Embed(title = "💩 You have failed to kill your target. You can try again when the next cycle starts."))

    @assassins.command()
    async def share(self, ctx, member : discord.Member):
        game = await self.choose_game(ctx.author)
        if game is None:
            return await ctx.send("No game running for you.")

        player = Player.get(game = game, user_id = ctx.author.id, alive = True)
        player_to_share_with = Player.get(game = game, user_id = member.id, alive = True)

        if player.id == player_to_share_with.id:
            return await ctx.send("Nice try.")

        player.cycle_immunity = True
        player.save()

        await member.send(f"{ctx.author} has shared their code with you. The code: {player.code}")

        await ctx.send("Okay. You are now immune to code leaks when this cycle ends.")


    @tasks.loop(minutes = 1)
    async def poll(self):
        for game in Game.select().where(Game.active == True):

            if not game.started:
                continue

            if len(game.players) > 1:
                if game.ended:
                    game.end()

            if game.cycle_ended:
                game.next_cycle()

def setup(bot):
    bot.add_cog(AssassinsCog(bot))
