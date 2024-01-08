import asyncio
import datetime
import re

import discord
import pytz

import src.config as config
from src.disc.helpers.embed import Embed
from src.disc.helpers.files import FileHelper
from src.utils.country import Country, CountryNotFound


class ConversionFailed(Exception): pass


class Skipped(Exception): pass


class Cancelled(Exception): pass


def _get_id_match(argument):
    return re.compile(r'([0-9]{15,21})$').match(argument)


class Waiter:
    __slots__ = ("verbose")

    def __init__(self, verbose=True):
        self.verbose = verbose

    @property
    def bot(self):
        return config.bot


class MessageWaiter(Waiter):
    __slots__ = (
        "ctx",
        "prompt",
        "end_prompt",
        "timeout",
        "show_instructions",
        "members",
        "channels",
        "converted",
        "max_words",
        "skippable",
        "skip_command",
        "cancellable",
        "cancel_command",
        "failures",
        "failure_limit"
    )

    def __init__(self,
                 ctx,
                 only_author=True,
                 prompt=None,
                 end_prompt=None,
                 timeout=360,
                 members=None,
                 channels=None,
                 show_instructions=True,
                 max_words=1,
                 skippable=False,
                 skip_command=">>skip",
                 cancellable=False,
                 cancel_command=">>cancel",
                 **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.prompt = prompt
        self.show_instructions = show_instructions
        self.end_prompt = end_prompt
        self.timeout = timeout
        self.members = members or []
        self.channels = channels or []
        self.max_words = max_words
        self.skippable = skippable
        self.skip_command = skip_command
        self.cancellable = cancellable
        self.cancel_command = cancel_command
        self.failures = 0
        self.failure_limit = 3

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

        if self.cancellable and message.content == self.cancel_command:
            raise Cancelled()

        if self.max_words is None:
            words = message.content
        else:
            words = " ".join(message.content.split()[:self.max_words])

        try:
            self.converted = self.convert(words)
        except ConversionFailed as e:
            if self.failures > self.failure_limit:
                self._send(message.channel, embed=Embed.error(f"Cancelled due to failing {self.failure_limit} times."))
                raise Cancelled()
            self._send(message.channel, embed=Embed.error(f"{e} Try again."))
            self.failures += 1
            return False

        return True

    @property
    def embed(self):
        embed = self.bot.get_base_embed(description=self.prompt)

        footer = []
        instructions = self.instructions
        if instructions is not None and self.show_instructions:
            footer.append(instructions)

        if self.skippable:
            footer.append(f"'{self.skip_command}' to skip")
        if self.cancellable:
            footer.append(f"'{self.cancel_command}' to cancel")

        if len(footer) > 0:
            embed.set_footer(text="\n".join(footer))

        return embed

    async def wait(self, raw=False):
        await self.ctx.channel.send(embed=self.embed)

        try:
            message = await self.bot.wait_for("message", timeout=self.timeout, check=self.check)
        except asyncio.TimeoutError:
            if self.verbose:
                await self.ctx.send("Timed out.")
            return None
        else:
            if self.end_prompt is not None:
                await message.channel.send(self.end_prompt.format(value=self.converted))

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

    def __init__(self, ctx, range=None, min=None, max=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.range = range

        if self.range is not None:
            self.min = self.range.start
            self.max = self.range.stop - 1
        else:
            self.min = min
            self.max = max

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

    def __init__(self, ctx, allowed_words=None, case_sensitive=True, min_length=1, max_length=2000, **kwargs):
        super().__init__(ctx, **kwargs)
        self.allowed_words = allowed_words or []
        self.case_sensitive = case_sensitive
        self.min_length = min_length
        self.max_length = max_length

    @property
    def instructions(self):
        if self.allowed_words:
            split = "'"
            sep = ","
            return f"options: {split}" + (f"{split}{sep} {split}".join(self.allowed_words)) + split

    def check(self, message):
        if not super().check(message):
            return False

        content = message.content if self.case_sensitive else message.content.lower()

        if self.allowed_words and content not in self.allowed_words:
            return False

        if len(content) > self.max_length:
            error_msg = f"Message is too long. Max length: {self.max_length}"
            asyncio.gather(message.channel.send(embed=Embed.error(error_msg)))
            return False

        if len(content) < self.min_length:
            error_msg = f"Message is too short. Min length: {self.min_length}"
            asyncio.gather(message.channel.send(embed=Embed.error(error_msg)))
            return False

        return True

    def convert(self, argument):
        return argument


class AttachmentWaiter(MessageWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, max_words=None, **kwargs)

    def convert(self, argument):
        return argument

    def check(self, message):
        if not super().check(message):
            return False

        if len(message.attachments) == 0:
            return False
        return True

    async def wait(self, store=True, raw=False):
        message = await super().wait(raw=True)
        if not raw:
            attachment = message.attachments[0]
            if store:
                return await FileHelper.store(await attachment.read(), attachment.filename)
            else:
                return attachment.url

        return message


class TimezoneWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

    @property
    def instructions(self):
        return "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"

    def convert(self, argument):
        try:
            return pytz.timezone(argument.title())
        except pytz.exceptions.UnknownTimeZoneError:
            raise ConversionFailed("Timezone not found.")


class CountryWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

    def convert(self, argument):
        try:
            country = Country(argument.upper())
        except CountryNotFound:
            raise ConversionFailed("Country not found.")

        return country


class RangeWaiter(StrWaiter):
    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, max_words=2, **kwargs)

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
    def __init__(self, ctx, enum, properties_to_skip=None, **kwargs):
        super().__init__(ctx, **kwargs)
        if properties_to_skip is None:
            properties_to_skip = []

        self.enum = enum
        self.allowed_words = [x.name for x in enum if x not in properties_to_skip]
        self.case_sensitive = False

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
        super().__init__(ctx, allowed_words=('yes', 'y', 'n', 'no'), case_sensitive=False, **kwargs)

    def convert(self, argument):
        lowered = argument.lower()

        if lowered in ("yes", "y"):
            return True
        elif lowered in ("no", "n"):
            return False

        raise ConversionFailed("Message needs to be yes/no.")


class MemberWaiter(MessageWaiter):

    @property
    def instructions(self):
        return "@mention"

    def get_id(argument):
        for id in re.findall(r'<@!?([0-9]+)>', argument):
            return int(id)

    def convert(self, argument):
        # commands.MemberConverter().convert(self.ctx, argument)
        id = self.get_id(argument)
        if id is not None:
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

    def __init__(self, ctx, before=None, after=None, **kwargs):
        super().__init__(ctx, **kwargs)

        self.before = before
        self.after = after

    @property
    def instructions(self):
        return "HH:MM:SS"

    def convert(self, argument):
        missing_count = 8 - len(argument)
        if missing_count > 0:
            for i in range(len(argument) + 1, 9):
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

    def __init__(self, ctx, before=None, after=None, **kwargs):
        super().__init__(ctx, min_length=len("1-1-1"), max_length=len("1994-02-06"), **kwargs)

        self.before = before
        self.after = after

    @property
    def instructions(self):
        return "YYYY-MM-DD"

    def convert(self, argument):
        try:
            year, month, day = argument.split("-")
            year = year.zfill(4)
            month = month.zfill(2)
            day = day.zfill(2)
            return datetime.datetime.strptime(year + month + day, "%Y%m%d").date()
        except ValueError:
            raise ConversionFailed("Message needs to be a date: YYYY-MM-DD.")

    def check(self, message):
        if not super().check(message):
            return False

        if self.before is not None and self.converted >= self.before:
            error_msg = f"Date can't be after {self.before}"
            asyncio.gather(message.channel.send(embed=Embed.error(error_msg)))
            return False

        if self.after is not None and self.converted <= self.after:
            error_msg = f"Date can't be before {self.after}"
            asyncio.gather(message.channel.send(embed=Embed.error(error_msg)))
            return False

        return True


class TimeDeltaWaiter(MessageWaiter):
    def __init__(self, ctx, *args, **kwargs):
        super().__init__(ctx, *args, max_words=2, **kwargs)

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

        possible_values = (
        "days", "seconds", "microseconds", "milliseconds", "minutes", "hours", "weeks", "months", "years")

        conversions = \
            {
                "months": lambda x: x * 4.348214155,
                "years": lambda x: x * 52.17856986008
            }

        if time in conversions:
            amount = conversions[time](amount)
            time = "weeks"

        if time not in possible_values:
            raise ConversionFailed("Time can only be: " + ", ".join(possible_values) + "\nExample: 2 **days**.")

        return datetime.timedelta(**{time: amount})

    def convert(self, argument):
        return self._convert(argument)


waiter_mapping = \
    {
        str: StrWaiter,
        int: IntWaiter,
        bool: BoolWaiter,
        datetime.date: DateWaiter,
        discord.Member: MemberWaiter,
        discord.TextChannel: TextChannelWaiter,
        discord.Role: RoleWaiter,
    }


class ReactionWaiter(Waiter):
    def __init__(self, ctx, message, emojis, members=None, channels=None):
        self.ctx = ctx
        self.message = message
        self.emojis = emojis
        self.members = members or []
        self.channels = channels or []

    async def add_reactions(self):
        for emoji in self.emojis:
            await self.message.add_reaction(emoji)

    async def clear_reactions(self):
        try:
            await self.message.clear_reactions()
        except:
            pass

    async def wait(self, raw=False, timeout=120, remove=False):
        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add',
                timeout=timeout,
                check=self.check)
        except asyncio.TimeoutError:
            return None

        if remove:
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass

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
