from enum import Enum

import discord

from src.utils.general import split_list
from src.discord.helpers.paginating import Page, Paginator

def prettify_value(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Enum):
        return value.name
    if value is None:
        return "N/A"
    return value

def limit_str(text, max = None):
    text = str(text)
    if max is not None and len(text) > max:
        return text[:max] + ".."
    else:
        return text

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
    def __init__(self, rows = None, sep = " | ", padding = 2):
        self._rows = rows or []
        self.sep = sep
        self.padding = padding

    @classmethod
    def from_list(cls, data, first_header = False, **kwargs):
        table = cls(**kwargs)
        i = 0
        for row in data:
            table.add_row(Row(row, header = first_header and i == 0))
            i += 1

        return table

    def to_paginator(self, ctx, rows_per_page):
        paginator = Paginator(ctx)
        row_groups = split_list([x for x in self._rows if not x.header], rows_per_page)
        header = self.header
        for rows in row_groups:
            table = self.__class__(rows = rows)
            table.add_row(header)
            embed = discord.Embed(color = ctx.guild_color)
            embed.description = table.generate()
            paginator.add_page(Page(embed))

        return paginator

    @property
    def header(self):
        for row in self._rows:
            if row.header:
                return row

    def add_row(self, row):
        if row.header:
            self._rows.insert(0, row)
        else:
            self._rows.append(row)

    @property
    def longests(self):
        longests = [len(x) for x in self._rows[0]]

        for row in self._rows:
            for i in range(len(row)):
                value = row[i]
                if len(value) > longests[i]:
                    longests[i] = len(value)

        return longests

    @property
    def row_count(self):
        return len(self._rows)

    def generate(self):
        lines = []
        longests = self.longests
        for row in self._rows:
            row_text = []
            for i in range(len(row)):
                row_text.append(row[i].ljust(longests[i]+self.padding) )
            lines.append(self.sep.join(row_text))

        header = self.header
        if header:
            equals = sum(longests) + ( len(header) * max(self.padding, 2) ) + len(self.sep) + self.padding
            lines.insert(1, "=" * equals )

        return "```md\n" + ( "\n".join(lines) ) + "```"

class Row(list):
    def __init__(self, data, header = False):
        self.header = header
        super().__init__([str(x) for x in data])

if __name__ == "__main__":
    pass