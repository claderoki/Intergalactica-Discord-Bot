import random
from abc import ABC
from typing import TypeVar, Generic, List


T = TypeVar("T")


class Probability(ABC):
    def __init__(self, probability: float):
        self.probability = probability


class Probabilities(Generic[T]):
    __slots__ = ('items',)

    def __init__(self, items: List[T]):
        self.items = items

    def __weights(self):
        return [x.probability for x in self.items]

    def choice(self) -> T:
        return random.choices(self.items, weights=self.__weights())[0]
