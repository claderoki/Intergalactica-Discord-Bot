

class Player:
    def __init__(self, bet):
        self.bet = bet
        self.correct_guesses   = 0
        self.incorrect_guesses = 0

    @property
    def dead(self):
        return self.incorrect_guesses >= 6

    def get_percentage_guessed(self, word):
        return (self.correct_guesses / len(word)) * 100

    def increment_incorrect(self):
        self.incorrect_guesses += 1

    def increment_correct(self):
        self.correct_guesses += 1
