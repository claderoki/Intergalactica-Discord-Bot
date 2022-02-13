class WeirdFont:
    __slots__ = ("char_mapping",)

    def __init__(self, alphabet):
        self.char_mapping = {}
        i = 0
        for letter in (string.ascii_lowercase + string.ascii_uppercase):
            self.char_mapping[letter] = alphabet[i]
            i += 1

    def __call__(self, text):
        return self.convert(text)

    def convert(self, text):
        new = []
        for letter in text:
            if letter in self.char_mapping:
                new.append(self.char_mapping[letter])
            else:
                new.append(letter)

        return "".join(new)

    @classmethod
    def from_full_alphabet(cls, text):
        pass

    @classmethod
    def regional(cls):
        return cls("🇦🇧🇨🇩🇪🇫🇬🇭🇯🇮🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿")

    @classmethod
    def italica(cls):
        return cls(
            "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘲𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘘𝘠𝘟")
