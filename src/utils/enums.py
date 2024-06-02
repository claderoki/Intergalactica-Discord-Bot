from enum import Enum


class Pronouns:
    def __init__(self, subject: str, object: str, possessive_adjective: str, possessive_pronoun: str):
        self.subject = subject
        self.object = object
        self.possessive_adjective = possessive_adjective
        self.possessive_pronoun = possessive_pronoun
        self.reflexive = object + 'self'

    @classmethod
    def male(cls):
        return cls('he', 'him', 'his', 'his')

    @classmethod
    def female(cls):
        return cls('she', 'her', 'her', 'hers')

    @classmethod
    def neutral(cls):
        return cls('they', 'them', 'their', 'theirs')

    @classmethod
    def animal(cls):
        return cls('it', 'it', 'its', 'its')


class Gender(Enum):
    male = 1
    female = 2
    other = 3

    def get_pronoun(self, object=False, plural=False):
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
