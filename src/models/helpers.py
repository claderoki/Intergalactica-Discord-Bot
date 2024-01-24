tables_to_create = []
tables_to_drop = []


def create():
    def wrapper(original_class):
        tables_to_create.append(original_class)
        return original_class
    return wrapper


def drop():
    def wrapper(original_class):
        tables_to_drop.append(original_class)
        return original_class
    return wrapper
