import datetime
import random
import asyncio

from dateutil.relativedelta import relativedelta

class WelcomeMessageCache:
    __slots__ = ("messages", "last_sent")

    def __init__(self):
        self.messages  = {}
        self.last_sent = None

class WelcomeMessage:
    _cache = {}

    __slots__ = ("guild_id", "channel", "message")

    def __init__(self,  guild_id, channel, message):
        self.guild_id = guild_id
        self.channel  = channel
        self.message  = message

        self._cache[guild_id] = WelcomeMessageCache()

    async def send(self, member):
        text = self.message.format(member = member)

        try:
            message = await self.channel.send(text)
        except:
            return

        cache = self._cache[member.guild.id]
        cache.messages[member.id] = message
        cache.last_sent = datetime.datetime.utcnow()

    async def remove(self, member):
        try:
            await self._cache[member.guild.id].messages[member.id].delete()
        except:
            pass

    def is_welcoming_message(self, message):
        """Whether or not a member sent a message welcoming someone new."""
        if message.author.bot:
            return False

        last_sent = self._cache[self.guild_id].last_sent

        if last_sent is None:
            return False

        time_here = relativedelta(datetime.datetime.utcnow(), last_sent)
        if time_here.minutes <= 5:
            return "welcome" in message.content.lower()

        return False

    async def react(self, message):
        emoji = random.choice(("💛", "🧡", "🤍", "💙", "🖤", "💜", "💚", "❤️"))
        asyncio.gather(message.add_reaction(emoji))
