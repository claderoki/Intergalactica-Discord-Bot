import typing

from src.models import Human, HumanItem, Item


class KnownItem:
    milkyway = "milky_way"
    orion_belt = "orions_belt"


class ItemCache:
    _code_mapping = {}
    _id_mapping = {}

    @classmethod
    def get_id(cls, code: str) -> int:
        id = cls._code_mapping.get(code)
        if id is not None:
            return id

        item = Item.select(Item.id).where(Item.code == code).first()
        if item is not None:
            cls._code_mapping[code] = item.id
            cls._id_mapping[item.id] = code
            return item.id

    @classmethod
    def get_code(cls, id: int) -> str:
        code = cls._id_mapping.get(id)
        if code is not None:
            return code

        item = Item.select(Item.id).where(Item.code == code).first()
        if item is not None:
            cls._code_mapping[code] = item.id
            cls._id_mapping[item.id] = code
            return item.id


class HumanCache:
    _id_mapping = {}

    @classmethod
    def get_id(cls, user_id: int) -> int:
        id = cls._id_mapping.get(user_id)
        if id is not None:
            return id

        human = Human.select(Human.id).where(Human.user_id == user_id).first()
        return human.id if human else None


class HumanRepository:
    @classmethod
    def __get_item_id(cls, item: typing.Union[str, int]):
        return item if isinstance(item, int) else ItemCache.get_id(item)

    @classmethod
    def get_item_amount(cls, user_id: int, item_id: int) -> int:
        human_id = HumanCache.get_id(user_id)
        item = (HumanItem.select(HumanItem.amount)
                .where(HumanItem.human == human_id)
                .where(HumanItem.item == item_id)
                .first())
        return item.amount if item else 0

    @classmethod
    def get_item_amounts(cls, user_id: int, item_identifiers: list, only_positives: bool = False) -> dict:
        mapping = {ItemCache.get_id(x): x for x in item_identifiers}

        items = (HumanItem.select(HumanItem.amount, HumanItem.item_id)
                 .where(HumanItem.human_id == HumanCache.get_id(user_id))
                 .where(HumanItem.item_id.in_(list(mapping.keys()))))

        amounts = {}
        for item in items:
            if not only_positives or item.amount > 0:
                amounts[mapping.get(item.item_id)] = item.amount
        return amounts

    @classmethod
    def increment_item(cls, user_id: int, item: typing.Union[str, int], amount: int):
        if amount == 0:
            return

        human_id = HumanCache.get_id(user_id)
        item_id = cls.__get_item_id(item)
        rows_affected = (HumanItem.update(amount=HumanItem.amount + amount)
                         .where(HumanItem.item == item_id)
                         .where(HumanItem.human == human_id)
                         .execute())

        if rows_affected == 0:
            pass
