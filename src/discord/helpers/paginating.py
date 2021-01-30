import asyncio
from enum import Enum

class Paginator:
    class Action(Enum):
        previous = 1
        next     = 2
        stop     = 3

    _actions = {"⬅️": Action.previous, "➡️" : Action.next, "⏹️": Action.stop}

    __slots__ = ("_pages", "_current_page", "_message", "_ctx")
    def __init__(self, ctx, pages = None):
        self._pages = pages or []
        self._current_page = 0
        self._message = None
        self._ctx = ctx

    def add_page(self, page):
        self._pages.append(page)

    @property
    def current_page(self):
        return self._pages[self._current_page]

    async def reload(self):
        page = self.current_page
        if self._message is None:
            self._message = await self._ctx.send(embed = page.embed)
        else:
            await self._message.edit(embed = page.embed)

    def previous(self):
        if self._current_page == 0:
            self._current_page = len(self._pages)-1
        else:
            self._current_page -= 1

        asyncio.gather(self.reload())

    def next(self):
        if self._current_page == len(self._pages)-1:
            self._current_page = 0
        else:
            self._current_page += 1

        asyncio.gather(self.reload())

    async def clear_reactions(self):
        try:
            await self._message.clear_reactions()
        except:
            pass

    async def remove_reaction(self, reaction, user):
        try:
            await self._message.remove_reaction(reaction, user)
        except:
            pass

    def __check(self, reaction, user):
        if user.id != self._ctx.author.id:
            return False

        emoji = str(reaction.emoji)
        if emoji not in self._actions:
            return False

        action = self._actions[emoji]

        if action == self.Action.stop:
            return True
        elif action == self.Action.next:
            self.next()
            asyncio.gather(self.remove_reaction(reaction, user))
        elif action == self.Action.previous:
            self.previous()
            asyncio.gather(self.remove_reaction(reaction, user))

        return False

    async def wait(self, timeout = 360):
        self.__show_pages()
        await self.reload()
        if len(self._pages) == 1:
            return
        for emoji in self._actions.keys():
            asyncio.gather(self._message.add_reaction(emoji))
        try:
            await self._ctx.bot.wait_for("reaction_add", timeout = timeout, check = self.__check)
        except asyncio.TimeoutError:
            pass

        asyncio.gather(self.clear_reactions())

    def __show_pages(self):
        for i, page in enumerate(self._pages):
            page.set_page_number(i+1, len(self._pages))

class Page:
    __slots__ = ("embed", )
    def __init__(self, embed):
        self.embed = embed

    def set_page_number(self, index, total):
        text = ""

        if self.embed.footer or self.embed.footer.text:
            text = self.embed.footer.text

        self.embed.set_footer(text = text + f"\nPage {index}/{total}")
