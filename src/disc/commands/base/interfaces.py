import abc


class Refreshable(abc.ABC):
    @abc.abstractmethod
    async def refresh(self):
        pass
