import asyncio
import random


class Game:
    bet = 5

    def __init__(self, players, ui):
        self.ui = ui
        self.players = players
        random.shuffle(self.players)

        self.board = [" "] * 10

    @property
    def game_over(self):
        if self.board_full:
            return True

        for player in self.players:
            if player.is_winner(self.board):
                return True

    def has_free_space(self, move):
        return self.board[move] == " "

    def get_winner(self):
        for player in self.players:
            if player.is_winner(self.board):
                return player

    @property
    def board_full(self):
        for i in range(1, 10):
            if self.has_free_space(i):
                return False
        return True

    @property
    def ai_only(self):
        for player in self.players:
            if not player.ai:
                return False
        return True

    def player_generator(self, check=lambda player: True):
        """check is a lambda that takes one parameter: player."""
        while True:
            for player in self.players:
                if check(player):
                    yield player

    async def start(self):
        players = self.player_generator()

        while not self.game_over:
            player = next(players)
            await self.ui.show_board(self, player)
            if player.ai:
                await asyncio.sleep(random.uniform(0.3, 2.1))
                move = player.get_best_move(self)
            else:
                move = await self.ui.get_move(self.board, player)

            player.move(self.board, move)

        await self.ui.show_board(self, player)

        await self.ui.game_over(self.get_winner())
