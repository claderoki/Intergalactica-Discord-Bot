

class Player:
    def __init__(self, identity, bet):
        self.identity = identity
        self.bet = bet
        self.correct_guesses   = 0
        self.incorrect_guesses = 0

    def __str__(self):
        return str(self.identity)

    @property
    def dead(self):
        return self.incorrect_guesses >= 6

    def get_percentage_guessed(self, word):
        return (self.correct_guesses / len(word)) * 100

    def increment_incorrect(self):
        self.incorrect_guesses += 1

    def increment_correct(self):
        self.correct_guesses += 1
