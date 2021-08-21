import asyncio
import random
from enum import Enum

import discord

from src.wrappers.zalgo import Zalgo

class Game:
    bet = 10

    def __init__(self, players, word : str, ui):
        self.ui = ui
        self.players = players

        self.letters_used = []
        self.words_used = []
        self.unedited_word = word
        self.word = Zalgo.dezalgofy(word.lower())

        self.board = ["-" for _ in word]

        self.winner = None

    def word_guessed(self):
        return "".join(self.board) == self.word

    def all_players_dead(self) -> bool:
        for player in self.players:
            if not player.dead:
                return False

        return True

    def living_players(self):
        i = 0
        while not self.all_players_dead():
            if not self.players[i].dead:
                yield self.players[i]

            i+=1
            if i > len(self.players)-1:
                i = 0

    def increment_incorrect(self, player):
        player.increment_incorrect()
        if player.dead and not self.all_players_dead():
            self.ui.send_error(f"{player.identity.member.mention} has perished.")

    async def start(self):
        await self.ui.refresh_board(self)
        living_players = self.living_players()

        while not self.all_players_dead() and not self.word_guessed():
            player = next(living_players)

            await self.ui.refresh_board(self, player)

            guess = await self.ui.get_guess(self.word, player, self.letters_used)

            if guess is None:
                self.increment_incorrect(player)
            elif len(guess) == 1:
                if guess in self.word and guess not in self.letters_used:
                    for i in range(len(self.word)):
                        if guess == self.word[i] and self.board[i] == "-":
                            self.board[i] = guess
                            player.increment_correct()

                    if self.word_guessed():
                        self.winner = player
                else:
                    self.increment_incorrect(player)

                self.letters_used.append(guess)

            else:
                if guess == self.word:
                    for _ in range(self.board.count("-")):
                        player.increment_correct()

                    self.board = list(self.word)

                    self.winner = player
                else:
                    self.words_used.append(guess)
                    self.increment_incorrect(player)

        await self.ui.refresh_board(self)

        await self.stop(self.calculate_reason())

    def calculate_reason(self):
        if self.winner is None:
            return self.Reasons.all_players_dead
        else:
            return self.Reasons.word_guessed

    async def stop(self, reason):
        await self.ui.stop(reason, self)

    class Reasons(Enum):
        all_players_dead = "Everybody lost"
        word_guessed     = "Word has been guessed"
