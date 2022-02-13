import random

from src.games.tictactoe.game.player import Player


class AIPlayer(Player):
    def __init__(self, identity, number):
        super().__init__(identity, number)

    @property
    def ai(self):
        return True

    def random_move_from_list(self, board, moves):
        possible_moves = []
        for i in moves:
            if board[i] == " ":
                possible_moves.append(i)

        if len(possible_moves) != 0:
            return random.choice(possible_moves)

    def get_board_copy(self, board):
        return [i for i in board]

    def get_best_move(self, game):
        # Check if we can win in the next move
        board = game.board

        for i in range(1, 10):
            copy = self.get_board_copy(board)
            if copy[i] == " ":
                self.move(copy, i)
                if self.is_winner(copy):
                    return i

        # Check if the player could win on their next move, and block them
        for i in range(1, 10):
            copy = self.get_board_copy(board)
            if copy[i] == " ":
                other = [x for x in game.players if x != self][0]
                other.move(copy, i)
                if other.is_winner(copy):
                    return i

        # Try to take one of the corners, if they are free
        move = self.random_move_from_list(board, [1, 3, 7, 9])
        if move != None:
            return move

        # Try to take the center, if it is free
        if board[5] == " ":
            return 5

        # Move on one of the sides
        return self.random_move_from_list(board, [2, 4, 6, 8])
