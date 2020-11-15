from enum import Enum

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

class Table:
    def __init__(self, rows = None):
        self.rows = rows or []
        self.sep = " | "

    @property
    def headers(self):
        for row in self.rows:
            if row.header:
                return row

    @property
    def longests(self):
        longests = [len(x) for x in self.rows[0]]

        for row in self.rows:
            for i in range(len(row)):
                value = row[i]
                if len(value) > longests[i]:
                    longests[i] = len(value)

        return longests

    def sort(self):
        self.rows.sort(key = lambda x : x.header, reverse = True)

    def generate(self):
        self.sort()
        headers = self.headers
        lines = []
        longests = self.longests
        self.padding = 2
        for row in self.rows:
            row_text = []
            for i in range(len(row)):
                row_text.append(row[i].ljust(longests[i]+self.padding) )
            lines.append(self.sep.join(row_text))

        equals = sum(longests) + (len(headers) * (self.padding) ) + len(self.sep) + self.padding
        lines.insert(1, "=" * equals )

        return "```md\n" + ( "\n".join(lines) ) + "```"

class Row(list):
    def __init__(self, data, header = False):
        self.header = header
        super().__init__(data)

if __name__ == "__main__":
    table = Table()
    table.rows.append(Row(["1", "5000", "Martha"]))
    table.rows.append(Row(["rank", "exp", "pigeon"], header = True))
    print(table.generate())
