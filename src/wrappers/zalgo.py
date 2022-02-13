import random
import unicodedata


class Zalgo:
    __slots__ = ("accents_up", "accents_down", "accents_middle", "max_accents_per_letter")

    diacritics = \
        {
            "up": ['̍', '̎', '̄', '̅', '̿', '̑', '̆', '̐', '͒', '͗', '͑', '̇', '̈', '̊', '͂', '̓', '̈́', '͊', '͋', '͌',
                   '̃', '̂', '̌', '͐', '́', '̋', '̏', '̽', '̉', 'ͣ', 'ͤ', 'ͥ', 'ͦ', 'ͧ', 'ͨ', 'ͩ', 'ͪ', 'ͫ', 'ͬ', 'ͭ',
                   'ͮ', 'ͯ', '̾', '͛', '͆', '̚'],
            "middle": ['̕', '̛', '̀', '́', '͘', '̡', '̢', '̧', '̨', '̴', '̵', '̶', '͜', '͝', '͞', '͟', '͠', '͢', '̸',
                       '̷', '͡'],
            "down": ['̖', '̗', '̘', '̙', '̜', '̝', '̞', '̟', '̠', '̤', '̥', '̦', '̩', '̪', '̫', '̬', '̭', '̮', '̯', '̰',
                     '̱', '̲', '̳', '̹', '̺', '̻', '̼', 'ͅ', '͇', '͈', '͉', '͍', '͎', '͓', '͔', '͕', '͖', '͙', '͚', ''],
        }

    def __init__(self, accents_up=(1, 3), accents_down=(1, 3), accents_middle=(1, 2), max_accents_per_letter=3):
        self.accents_up = accents_up
        self.accents_down = accents_down
        self.accents_middle = accents_middle
        self.max_accents_per_letter = max_accents_per_letter

    def zalgofy(self, text):
        """
        Zalgofy a string
        """
        new_chars = []
        for char in text:

            new_chars.append(char)

            if not char.isalpha():
                continue

            number_of_accents = \
                {
                    "up": random.randint(*self.accents_down),
                    "middle": random.randint(*self.accents_middle),
                    "down": random.randint(*self.accents_up)
                }

            accent_count = 0
            while sum(number_of_accents.values()) != 0 and accent_count < self.max_accents_per_letter:
                choice = random.choice([k for k, v in number_of_accents.items() if v != 0])
                new_chars.append(random.choice(self.diacritics[choice]))
                number_of_accents[choice] -= 1
                accent_count += 1

        return "".join(new_chars)

    @staticmethod
    def dezalgofy(text):
        """
        Removes all diacritis from a string.
        Source : https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string
        """
        return u"".join([c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)])


if __name__ == "__main__":
    z = Zalgo()
    print(z.zalgofy("Name"))
