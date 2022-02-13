from src.models import Human, HumanItem, Item


class KnownItem:
    milkyway = "milky_way"
    orion_belt = "orions_belt"


class ItemCache:
    _code_mapping = {}

    @classmethod
    def get_id(cls, code: str) -> int:
        id = cls._code_mapping.get(code)
        if id is not None:
            return id

        item = Item.select(Item.id).where(Item.code == code).first()
        return item.id if item else None


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
    def get_item_amount(cls, user_id: int, item_code: str) -> int:
        item_id = ItemCache.get_id(item_code)
        human_id = HumanCache.get_id(user_id)
        item = (HumanItem.select(HumanItem.amount)
                .where(HumanItem.human == human_id)
                .where(HumanItem.item == item_id)
                .first())
        return item.amount if item else 0

    @classmethod
    def get_item_amounts(cls, user_id: int, item_codes: list, only_positives: bool = False) -> dict:
        mapping = {ItemCache.get_id(x): x for x in item_codes}

        items = (HumanItem.select(HumanItem.amount, HumanItem.item_id)
                 .where(HumanItem.human_id == HumanCache.get_id(user_id))
                 .where(HumanItem.item_id.in_(list(mapping.keys()))))

        amounts = {}
        for item in items:
            if not only_positives or item.amount > 0:
                amounts[mapping.get(item.item_id)] = item.amount
        return amounts
