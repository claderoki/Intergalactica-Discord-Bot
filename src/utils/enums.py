from enum import Enum

class Gender(Enum):
    male      = 1
    female    = 2
    other     = 3

    def get_pronoun(self, object = False, plural = False):
        if plural:
            return "them" if object else "they"
        if self == self.male:
            return "him" if object else "he"
        elif self == self.female:
            return "her" if object else "she"
        else:
            return "it"

    def get_posessive_pronoun(self):
        if self == self.male:
            return "his"
        elif self == self.female:
            return "her"
        else:
            return "its"
