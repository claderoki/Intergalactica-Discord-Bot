import random
import asyncio
import datetime
import math

from dateutil import relativedelta
import discord
import peewee

import src.config as config
from .base import BaseModel


def cache(func):
    name = func

    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "_cache"):
            self._cache = {}

        if name not in self._cache:
            self._cache[name] = func.__get__()

        return self._cache[name]

    return wrapper

class Leak(BaseModel):
    class Meta:
        table_name = "assassins_leak"

    _to = None
    _from =  None

class Game(BaseModel):
    class Meta:
        table_name = "assassins_game"

    players_left_for_final_round = 3

    guild_id                       = peewee.BigIntegerField ()
    active                         = peewee.BooleanField    (default = True)
    frequency_in_minutes           = peewee.IntegerField    (default = 5)
    cycle_count                    = peewee.IntegerField    (default = 0)
    round_count                    = peewee.IntegerField    (default = 0)
    initial_players_at_round_start = peewee.IntegerField    (null = True)
    cycle_start                    = peewee.DateTimeField   (null = True)

    @property
    def started(self):
        return self.cycle_count > 0 and self.round_count > 0

    @property
    def final_round(self):
        return len(self.living_players) <= self.players_left_for_final_round

    @property
    def living_players(self):
        return self.players.where(Player.alive == True)

    async def log(self, *args, **kwargs):
        #TODO: setup a non hardcoded way for logs.
        if self.guild_id == 742146159711092757:
            log_channel_id = 754056523277271170
        elif self.guild_id == 761624318291476482:
            log_channel_id = 763180468061077524
        else:
            return

        channel = self.guild.get_channel(log_channel_id)
        return await channel.send(*args, **kwargs)

    @property
    def ended(self):
        return len(self.living_players) <= 1


    def end(self):
        players = list(self.living_players)
        assert len(players) == 1, "Can't have more than one winner."

        winner = players[0]

        self.active = False
        self.save()

        asyncio.gather(self.log(f"The game has ended. Winner: {winner.member}"))

    @property
    def new_round_available(self):
        if self.initial_players_at_round_start is None:
            return True

        if self.final_round:
            return False

        players = self.living_players
        return len(players) <= math.ceil(self.initial_players_at_round_start / 2)

    def leak_player_codes(self, players = None):
        if players is None:
            players = list(self.living_players)

        coros = []

        for player in players:
            if player.cycle_immunity:
                continue

            leak_count = 0

            players_without_player = [x for x in players if x.id != player.id]
            random.shuffle(players_without_player)

            for player_to_notify in players_without_player[:self.cycle_count-1]:
                coros.append(player_to_notify.member.send(f"**{player.member}**s code is **{player.code}**"))
                leak_count += 1

            if leak_count > 0:
                coros.append(player.member.send(f"Oh no! Your code was leaked to {leak_count} people."))

        asyncio.gather(*coros)


    def assign_new_code_to_players(self , players = None):

        if players is None:
            players = list(self.living_players)

        possibly_codes = [str(x) for x in range(10,100)]
        random.shuffle(possibly_codes)

        for player in players:
            player.code = possibly_codes.pop()
            player.save()

    def assign_new_targets(self, players = None):
        if players is None:
            players = list(self.living_players)

        random.shuffle(players)

        for i in range(len(players)):
            player = players[i]
            target_index = 0 if i == len(players)-1 else i + 1
            target = players[target_index]

            player.kill_command_available = True

            player.target = target
            player.save()

    def send_status_to_all_players(self, players = None):
        if players is None:
            players = list(self.living_players)

        asyncio.gather(*[x.send_status() for x in players])

    def next_round(self):

        self.cycle_count = 0

        self.round_count += 1
        players = list(self.living_players)

        self.initial_players_at_round_start = len(players)

        self.assign_new_targets(players)
        self.assign_new_code_to_players(players)
        self.send_status_to_all_players(players)

        embed = discord.Embed(
            title = f"Round {self.round_count}",
            description = f"Round {self.round_count} has started!"
                          f"New codes and targets have been assigned to all surviving players."
                          f"There are currently {len(players)} players alive."
                          f"The round ends when {math.ceil(self.initial_players_at_round_start / 2)} players have died, try to survive!"
        )

        dm_embed = discord.Embed(
            title = f"A new round has started!",
            description = f"Your goal is to make it to the end of the round by any means necessary. Learn your target's secret code to assassinate them, and protect your own code from the person who's targeting you. But be careful: every x hours, a cycle passes and your code will leak to random people in the game, and the only way to stop it is by sharing your code with someone you trust!"
        )

        dm_embed.add_field( name = f"Killing your target",
                         value = "Kill your target with the following command: `kill`. Make sure you know their code before you attempt though - you only get one wrong try per cycle! ",
                         inline = False )

        dm_embed.add_field( name = f"Sharing your code",
                         value = "Share your code with someone you trust with the following command: `share`. Each time you do this you stop the game from leaking your code to random players!",
                         inline = False )


        coros = [self.log(embed = embed)]

        for player in players:
            coros.append(player.member.send(embed = dm_embed))

        asyncio.gather(*coros)

        self.next_cycle()

        self.save()


    def start(self):
        self.active = True
        self.next_round()

    def start_final_round(self):
        pass

    def next_cycle(self):
        first_cycle = self.cycle_count == 0
        self.cycle_count += 1
        players = list(self.living_players)

        if not self.final_round and not first_cycle:
            self.leak_player_codes(players)

        self.cycle_start = datetime.datetime.utcnow()
        self.save()

        embed = discord.Embed(
            title = f"Cycle {self.cycle_count}",
            description = f"A new cycle has started! When the cycle ends each player's code will be leaked to {self.cycle_count} players.")

        dm_embed = discord.Embed(
            title = f"Round {self.round_count} Cycle {self.cycle_count+1}",
            description = f"When this cycle will your code will leak to {self.cycle_count+1} random players. Prevent this by sharing your code with a player you trust!"
        )

        for _embed in (embed, dm_embed):
            _embed.set_footer(text = "Cycle ends at")
            _embed.color = self.bot.get_dominant_color(self.guild)
            _embed.timestamp = self.cycle_end_date

        coros = []
        for player in players:
            coros.append(player.member.send(embed = dm_embed))
        coros.append(self.log(embed = embed))
        asyncio.gather(*coros)

        Player.update(kill_command_available = True, cycle_immunity = False).where( (Player.game == self) & (Player.alive == True) ).execute()

    @property
    def minutes_until_next_cycle(self):
        return relativedelta.relativedelta(self.cycle_end_date, datetime.datetime.utcnow()).minutes

    @property
    def cycle_end_date(self):
        if self.cycle_start is not None:
            return self.cycle_start + datetime.timedelta(minutes = self.frequency_in_minutes)

    @property
    def cycle_ended(self):
        if self.cycle_start is None:
            return True

        return datetime.datetime.utcnow() >= self.cycle_end_date

class KillMessage(BaseModel):
    class Meta:
        table_name = "assassins_kill_message"

    value = peewee.CharField(unique = True, max_length = 130)

class Player(BaseModel):
    class Meta:
        table_name = "assassins_player"

    user_id                 = peewee.BigIntegerField ()
    code                    = peewee.CharField       (null = True)
    game                    = peewee.ForeignKeyField (Game, backref = "players", on_delete = "CASCADE")
    alive                   = peewee.BooleanField    (default = True)
    kill_command_available  = peewee.BooleanField    (default = True)
    target                  = peewee.ForeignKeyField ("self", null = True)
    kills                   = peewee.IntegerField    (default = 0)
    cycle_immunity          = peewee.BooleanField    (default = False)

    async def send_status(self):
        if self.member is not None:
            await self.member.send(embed = self.embed)

    @property
    def embed(self):
        embed = discord.Embed(title = f"Status for {self.member}")
        embed.add_field(name = "🎯 Your Target", value = self.target.member, inline = False)
        embed.add_field(name = "🤐 Your Code", value = self.code, inline = False)

        return embed

    @property
    def member(self):
        if self._member is None:
            self._member = self.game.guild.get_member(self.user_id)

        return self._member