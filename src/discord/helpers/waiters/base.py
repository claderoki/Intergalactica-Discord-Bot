import asyncio
import datetime
import re

import pytz
import pycountry
import discord

import src.config as config
from src.discord.helpers.embed import Embed

class ConversionFailed(Exception): pass
class Skipped(Exception): pass

def _get_id_match(argument):
    return re.compile(r'([0-9]{15,21})$').match(argument)

class Waiter:
    __slots__ = ("verbose")
    def __init__(self, verbose = True):
        self.verbose = verbose

    @property
    def bot(self):
        return config.bot

class MessageWaiter(Waiter):
    __slots__ = ("ctx","prompt", "end_prompt", "timeout", "members", "channels", "converted", "max_words", "skippable", "skip_command")

    def __init__(self,
    ctx,
    only_author = True,
    prompt = None,
    end_prompt = None,
    timeout = 360,
    members = None,
    channels = None,
    max_words = 1,
    skippable = False,
    skip_command = ">>skip",
    **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.prompt = prompt
        self.end_prompt = end_prompt
        self.timeout = timeout
        self.members = members or []
        self.channels = channels or []
        self.max_words = max_words
        self.skippable = skippable
        self.skip_command = skip_command

        self.channels.append(ctx.channel)


        if only_author:
            self.members.append(ctx.author)

    @property
    def instructions(self):
        pass

    def __init_subclass__(cls):
        if not hasattr(cls, "convert"):
            raise Exception("This class needs the convert method.")

    def _send(self, channel, *args, **kwargs):
        loop = asyncio.get_event_loop()
        coro = channel.send(*args, **kwargs)
        loop.create_task(coro)

    def convert(self, argument):
        raise NotImplementedError()

    def check(self, message):
        if self.members and message.author.id not in [x.id for x in self.members]:
            return False

        if message.channel.id not in [x.id for x in self.channels]:
            return False

        if self.skippable and message.content == self.skip_command:
            raise Skipped()

        if self.max_words is None:
            words = message.content.split()
        else:
            words = message.content.split()[:self.max_words]

        try:
            self.converted = self.convert(" ".join(words))
        except ConversionFailed as e:
            self._send(message.channel, embed = Embed.error(str(e) + " Try again."))
            return False

        return True

    @property
    def embed(self):
        embed = self.ctx.bot.base_embed(description = self.prompt)

        footer = []
        instructions = self.instructions
        if instructions is not None:
            footer.append(instructions) 
        if self.skippable:
            footer.append(f"This can be skipped with '{self.skip_command}'")

        if len(footer) > 0:
            embed.set_footer( text = "\n".join(footer))

        return embed

    async def wait(self, raw = False):
        await self.ctx.channel.send(embed = self.embed)

        try:
            message = await self.ctx.bot.wait_for("message", timeout=self.timeout, check = self.check)
        except asyncio.TimeoutError:
            if self.verbose:
                await self.ctx.send("Timed out.")
            return None
        else:
            if self.end_prompt is not None:
                await message.channel.send(self.end_prompt.format(value = self.converted))

            if not raw:
                return self.converted
            else:
                return message


class IntWaiter(MessageWaiter):

    __slots__ = ("range", "min", "max")

    @property
    def instructions(self):
        if self.min is None and self.max is None:
            return None

        instructions = []
        if self.min is not None:
            instructions.append(f"min={self.min}")
        if self.max is not None:
            instructions.append(f"max={self.max}")

        return ", ".join(instructions)

    def __init__(self, ctx, range = None, min = None, max = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.range = range

        if self.range is not None:
            self.min = self.range.start
            self.max = self.range.stop-1
        else:
            self.min   = min
            self.max   = max

    def check(self, message):
        if not super().check(message):
            return False

        if self.min is not None and self.converted < self.min:
            return False

        if self.max is not None and self.converted > self.max:
            return False

        return True

    def convert(self, argument):
        try:
            return int(argument)
        except ValueError:
            raise ConversionFailed("Message needs to be a number.")

class FloatWaiter(IntWaiter):
    def convert(self, argument):
        try:
            return float(argument)
        except ValueError:
            raise ConversionFailed("Message needs to be a number.")

class StrWaiter(MessageWaiter):
    __slots__ = ("allowed_words", "case_sensitive", "min_length", "max_length")

    def __init__(self, ctx, allowed_words = [], case_sensitive = True, min_length = 1, max_length = 2000, **kwargs):
        super().__init__(ctx, **kwargs)
        self.allowed_words  = allowed_words
        self.case_sensitive = case_sensitive
        self.min_length     = min_length
        self.max_length     = max_length


    def check(self, message):
        if not super().check(message):
            return False

        content = message.content if self.case_sensitive else message.content.lower()

        if self.allowed_words and content not in self.allowed_words:
            return False

        if len(content) > self.max_length:
            return False

        if len(content) < self.min_length:
            return False

        return True

    def convert(self, argument):
        return argument

class TimezoneWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

    def convert(self, argument):
        return pytz.timezone(argument)

class CountryWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, min_length = 2, max_length = 3, **kwargs)

    @property
    def instructions(self):
        return "NL / NLD"

    def convert(self, argument):
        if len(argument) not in (2,3):
            raise ConversionFailed("Message needs to be a country code.")

        country = pycountry.countries.get(**{f"alpha_{len(argument)}": argument.upper()})
        if country is None:
            raise ConversionFailed("Country not found.")

        return country

class RangeWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, max_words = 2, **kwargs)

    @property
    def instructions(self):
        return "<min> <max>"

    def convert(self, argument):
        try:
            min, max = [int(x) for x in argument.split()]
            return range(min, max)
        except:
            raise ConversionFailed("Message needs to be a range.")

class EnumWaiter(StrWaiter):
    def __init__(self, ctx, enum, **kwargs):
        super().__init__(ctx, **kwargs)
        self.enum = enum
        self.allowed_words = [x.name for x in enum]
        self.case_sensitive = False

    @property
    def instructions(self):
        split = "'"
        sep = ","
        return f"allowed words: {split}" + (f"{split}{sep} {split}".join(self.allowed_words)) + split

    def convert(self, argument):
        try:
            return self.enum[argument.lower()]
        except:
            raise ConversionFailed("Message not valid.")


class BoolWaiter(StrWaiter):

    @property
    def instructions(self):
        return "yes / no"

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, allowed_words = ('yes', 'y', 'n', 'no'), case_sensitive=False, **kwargs)

    def convert(self, argument):
        lowered = argument.lower()

        if lowered in ("yes","y"):
            return True
        elif lowered in ("no", "n"):
            return False

        raise ConversionFailed("Message needs to be yes/no.")


class MemberWaiter(MessageWaiter):

    @property
    def instructions(self):
        return "@mention"

    def convert(self, argument):
        match = re.match(r'<@!?([0-9]+)>$', argument)
        if match:
            id = int(match.group(1))
            return self.ctx.guild.get_member(id)

        raise ConversionFailed("Message needs to be a @mention.")

class TextChannelWaiter(MessageWaiter):

    @property
    def instructions(self):
        return "#mention"

    def convert(self, argument):
        match = re.match(r'<#([0-9]+)>$', argument)
        if match:
            id = int(match.group(1))
            return self.ctx.guild.get_channel(id)

        raise ConversionFailed("Message needs to be a #mention.")


class RoleWaiter(MessageWaiter):

    def convert(self, argument):
        guild = self.ctx.guild

        match = _get_id_match(argument) or re.match(r'<@&([0-9]+)>$', argument)
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = discord.utils.get(guild._roles.values(), name=argument)

        if result is None:
            raise ConversionFailed("Role not found.")
        return result


class TimeWaiter(MessageWaiter):
    __slots__ = ("before", "after")

    def __init__(self, ctx, before = None, after =None, **kwargs):
        super().__init__(ctx, **kwargs)

        self.before = before
        self.after  = after

    def convert(self, argument):

        missing_count = 8 - len(argument)
        if missing_count > 0:
            for i in range(len(argument)+1, 9):
                if i % 3 == 0:
                    argument += ":"
                else:
                    argument += "0"

        try:
            hours, minutes, seconds = [int(x) for x in argument.split(":")]
        except:
            raise ConversionFailed("Needs to be HH:MM:SS.")

        return datetime.time(hours, minutes, seconds)




class DateWaiter(StrWaiter):

    __slots__ = ("before", "after")

    def __init__(self, ctx, before = None, after =None, **kwargs):
        super().__init__(ctx, min_length = len("1-1-1"), max_length = len("06-02-1994"), **kwargs)

        self.before = before
        self.after  = after

    @property
    def instructions(self):
        return "YYYY-MM-DD"

    def convert(self, argument):
        try:
            year,month,day = argument.split("-")
            year = year.zfill(4)
            month = month.zfill(2)
            day = day.zfill(2)
            return datetime.datetime.strptime(year + month + day,"%Y%m%d").date()
        except ValueError:
            raise ConversionFailed("Message needs to be a date: YYYY-MM-DD.")


    def check(self, message):
        if not super().check(message):
            return False

        if self.before is not None and self.converted >= self.before:
            return False

        if self.after is not None and self.converted <= self.after:
            return False

        return True


class TimeDeltaWaiter(MessageWaiter):

    @property
    def instructions(self):
        return "Examples: '2 days', '1 hour', '10 weeks'"

    @staticmethod
    def _convert(argument):
        amount, time = argument.split()

        if not amount.isdigit():
            raise ConversionFailed("Needs to be a number. example: **2** hours.")

        amount = int(amount)

        if not time.endswith("s"):
            time = time + "s"

        possible_values = ("days", "seconds", "microseconds", "milliseconds", "minutes", "hours", "weeks", "months", "years")

        conversions =\
        {
            "months" : lambda x : x * 4.348214155,
            "years"  : lambda x : x * 52.17856986008
        }

        if time in conversions:
            amount = conversions[time](amount)
            time = "weeks"


        if time not in possible_values:
            raise ConversionFailed("Time can only be: " + ", ".join(possible_values) + "\nExample: 2 **days**.")

        return datetime.timedelta(**{time : amount })

    def convert(self, argument):
        return self._convert(argument)


waiter_mapping = \
{
    str                 : StrWaiter,
    int                 : IntWaiter,
    bool                : BoolWaiter,
    datetime.date       : DateWaiter,
    discord.Member      : MemberWaiter,
    discord.TextChannel : TextChannelWaiter,
    discord.Role        : RoleWaiter,
}

class ReactionWaiter(Waiter):
    def __init__(self, ctx, message, emojis, members = [], channels = [] ):
        self.ctx = ctx
        self.message = message
        self.emojis = emojis
        self.members = members
        self.channels = channels

    async def add_reactions(self):
        for emoji in self.emojis:
            await self.message.add_reaction(emoji)

    async def clear_reactions(self):
        try:
            await self.message.clear_reactions()
        except: pass

    async def wait(self, raw = False, timeout = 45, remove = False):
        reaction, user = await self.ctx.bot.wait_for(
            'reaction_add',
            timeout = timeout,
            check   = self.check)

        if remove:
            try:
                await self.message.remove_reaction(reaction, user)
            except: pass

        if raw:
            return reaction, user
        else:
            return str(reaction.emoji)


    def check(self, reaction, user):
        if reaction.message.id != self.message.id:
            return False

        if self.channels:
            if reaction.message.channel.id not in [x.id for x in self.channels]:
                return False

        if self.members:
            if user.id not in [x.id for x in self.members]:
                return False

        if str(reaction.emoji) not in self.emojis:
            return False

        return True
