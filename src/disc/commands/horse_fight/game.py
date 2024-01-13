
class Horse:
    __slots__ = ('identifier', 'location', 'time_arrived')

    def __init__(self, identifier: str):
        self.identifier = identifier
        self.location = 0

    def __str__(self):
        return self.identifier
