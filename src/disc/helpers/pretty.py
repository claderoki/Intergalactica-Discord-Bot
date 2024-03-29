import datetime
from enum import Enum

import discord

from src.disc.helpers.paginating import Page, Paginator
from src.utils.general import split_list


class TimeDeltaHelper:
    @classmethod
    def _append_single_unit(cls, value: int, name: str, messages: list) -> str:
        if len(messages) < 2 and value > 0:
            name = name if value == 1 else name + "s"
            messages.append(f"{value} {name}")

    @classmethod
    def prettify(cls, value: datetime.timedelta) -> str:
        # Does it make sense to call abs?
        seconds = abs(value.total_seconds())

        if seconds < 60:
            # just an override to make it a bit more efficient in the case of small deltas.
            return f"{int(seconds)} seconds"

        years = int((seconds / 2592000) / 12)
        months = int((seconds / 2592000) % 30)
        days = int((seconds / 86400) % 30)
        hours = int((seconds / 3600) % 24)
        minutes = int((seconds % 3600) / 60)
        seconds = int(seconds % 60)

        messages = []
        cls._append_single_unit(years, "year", messages)
        cls._append_single_unit(months, "month", messages)
        cls._append_single_unit(days, "day", messages)
        cls._append_single_unit(hours, "hour", messages)
        cls._append_single_unit(minutes, "minute", messages)
        cls._append_single_unit(seconds, "second", messages)
        return " and ".join(messages)


def prettify_value(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, datetime.timedelta):
        return TimeDeltaHelper.prettify(value)
    if value is None:
        return "N/A"
    return value


def limit_str(text, max=None):
    text = str(text)
    if max is not None and len(text) > max:
        return text[:max] + ".."
    else:
        return text


def prettify_dict(data, emojis=None):
    if emojis is not None and len(data) != len(emojis):
        raise Exception("Not equal!")

    lines = []
    longest = max([len(x) for x in data.keys()])

    ljust = lambda x: x.ljust(longest + 2)
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
    def __init__(self, rows=None, sep=" | ", padding=2, title=None):
        self._rows = rows or []
        self.sep = sep
        self.padding = padding
        self.title = None

    @classmethod
    def from_list(cls, data, first_header=False, **kwargs):
        table = cls(**kwargs)
        i = 0
        for row in data:
            table.add_row(Row(row, header=first_header and i == 0))
            i += 1

        return table

    def sort(self, by, type: str):
        header = self.header
        self._rows.remove(header)
        self._rows.sort(key=lambda x: type(x[by]), reverse=True)
        self._rows.insert(0, header)

    def to_paginator(self, ctx, rows_per_page):
        paginator = Paginator(ctx)
        row_groups = split_list([x for x in self._rows if not x.header], rows_per_page)
        header = self.header
        for rows in row_groups:
            table = self.__class__(rows=rows)
            if header is not None:
                table.add_row(header)
            embed = discord.Embed(color=ctx.guild_color)
            if self.title is not None:
                embed.title = self.title

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
                row_text.append(row[i].ljust(longests[i] + self.padding))
            lines.append(self.sep.join(row_text))

        header = self.header
        if header:
            equals = sum(longests) + (len(header) * max(self.padding, 2)) + len(self.sep) + self.padding
            lines.insert(1, "=" * equals)

        return "```md\n" + ("\n".join(lines)) + "```"


class Row(list):
    def __init__(self, data, header=False):
        self.header = header
        super().__init__([str(x) for x in data])


if __name__ == "__main__":
    pass
