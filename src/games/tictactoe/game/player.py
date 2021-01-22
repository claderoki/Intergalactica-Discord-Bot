

class Player:
    def __init__(self, identity, number):
        self.identity = identity
        self.number = number

    @property
    def ai(self):
        return False

    def __str__(self):
        return str(self.identity)

    @property
    def symbol(self):
        return "╳" if self.number == 1 else "O"

    def move(self, board, move):
        board[move] = self.symbol

    def is_winner(self, board):
        le = self.symbol
        bo = board

        return ((bo[7] == le and bo[8] == le and bo[9] == le) or # across the top
        (bo[4] == le and bo[5] == le and bo[6] == le) or # across the middle
        (bo[1] == le and bo[2] == le and bo[3] == le) or # across the bottom
        (bo[7] == le and bo[4] == le and bo[1] == le) or # down the left side
        (bo[8] == le and bo[5] == le and bo[2] == le) or # down the middle
        (bo[9] == le and bo[6] == le and bo[3] == le) or # down the right side
        (bo[7] == le and bo[5] == le and bo[3] == le) or # diagonal
        (bo[9] == le and bo[5] == le and bo[1] == le)) # diagonal
