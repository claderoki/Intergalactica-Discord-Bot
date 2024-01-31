
class Stat:
    def __init__(self, type: str, format=None):
        self.type = type
        self.format = format

    def combine(self, other: 'Stat'):
        pass

    def readable(self) -> str:
        if self.format is not None:
            return self.format(self)
        return self.type


class CountableStat(Stat):
    def __init__(self, type: str, format=None):
        super().__init__(type, format)
        self.count = 1

    def combine(self, other: 'CountableStat'):
        self.count += other.count


class ComparingStat(Stat):
    def __init__(self, type: str, value, additional=None, format=None):
        super().__init__(type, format)
        self.value = value
        self.additional = additional

    def combine(self, other: 'ComparingStat'):
        if other.value > self.value:
            self.value = other.value
            self.additional = other.additional
