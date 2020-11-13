from enum import Enum

class Table:
    pass

def prettify_value(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Enum):
        return value.name
    if value is None:
        return "N/A"
    return value

def prettify_dict(data, emojis = None):
    if emojis is not None and len(data) != len(emojis):
        raise Exception("Not equal!")

    lines = []
    longest = max([len(x) for x in data.keys() ])

    ljust = lambda x : x.ljust(longest+2)
    i = 0
    for key, value in data.items():
        value = prettify_value(value)
        if emojis is not None:
            lines.append(f"{emojis[i]} {ljust(key)} {value}")
        else:
            lines.append(f"{ljust(key)} {value}")
        i += 1

    return "\n".join(lines)
