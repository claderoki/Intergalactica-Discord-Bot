import asyncio
from enum import Enum

import discord

from src.discord.helpers.waiters import MemberWaiter
import src.config as config
from src.discord.helpers import KnownGuild

class SimpleVote:
    class Option(Enum):
        yes  = "✅"
        no   = "❎"
        skip = "❓"

    __slots__ = ("option", "count")

    def __init__(self, option: Option, count: int = 0):
        self.option = option
        self.count = count

    def increment_count(self):
        self.count += 1

class SimplePoll:
    """A simple event based vote, wont be 'finished' until every member in the channel reacted."""

    @classmethod
    def add_guild_data(cls, guild_id: int, vote_channel_id: int, result_channel_id: int):
        cls.guild_data[guild_id] = {"vote_channel": vote_channel_id, "result_channel": result_channel_id}

    options = [x.value for x in SimpleVote.Option]

    guild_data = {}

    __slots__ = ("message", "question", "votes", "member_count")

    def __init__(self, message: discord.Message, votes: list, member_count: int):
        self.message      = message
        self.question     = message.content
        self.votes        = votes
        self.member_count = member_count

    @classmethod
    async def from_payload(cls, payload) -> "SimplePoll":
        channel      = config.bot.get_channel(payload.channel_id)
        message      = await channel.fetch_message(payload.message_id)
        votes        = await cls.get_votes(message)
        member_count = len([x for x in message.channel.members if not x.bot and x.id not in (649407938745598004, 516136653627064320)])

        return cls(message, votes, member_count)

    @classmethod
    def is_eligible(cls, payload) -> bool:
        if payload.member is None or payload.member.bot:
            return False
        if str(payload.emoji) not in cls.options:
            return False
        if payload.guild_id is None:
            return False

        channel_data = cls.guild_data.get(payload.guild_id)
        if channel_data is None:
            return False
        if payload.channel_id != channel_data["vote_channel"]:
            return False

        return True

    @classmethod
    async def get_votes(cls, message: discord.Message) -> list:
        reactions = [x for x in message.reactions if str(x.emoji) in cls.options]
        all_user_ids = set()
        votes = []
        for reaction in reactions:
            vote = SimpleVote(SimpleVote.Option(str(reaction.emoji)))
            votes.append(vote)

            async for user in reaction.users():
                if user.bot or user.id in all_user_ids:
                    continue
                vote.increment_count()
                all_user_ids.add(user.id)

        return votes

    def should_finish(self) -> bool:
        total_votes = sum(x.count for x in self.votes)
        return total_votes >= self.member_count

    def is_selfie_vote(self):
        if self.message.guild.id != KnownGuild.intergalactica:
            return False
        return "selfie access" in self.message.content.lower() or "selfie perm" in self.message.content.lower()

    def assign_selfie_role(self):
        user_id = MemberWaiter.get_id(self.message.content)
        member = self.message.guild.get_member(user_id)
        if member is None:
            return False
        selfie_role = self.message.guild.get_role(744703465086779393)
        asyncio.gather(member.add_roles(selfie_role))
        return True

    def finish(self):
        channel = self.message.guild.get_channel(self.guild_data[self.message.guild.id]["result_channel"])
        embed = discord.Embed(color = config.bot.get_dominant_color(None))

        lines = []
        lines.append("*(all members finished voting)*")
        lines.append("\n")

        skip_count       = sum(x.count for x in self.votes if x.option == SimpleVote.Option.skip)
        valid_vote_count = self.member_count - skip_count

        for vote in self.votes:
            if vote.option == SimpleVote.Option.skip:
                continue

            try:
                percentage = (vote.count / valid_vote_count) * 100
                percentage = int(percentage) if percentage % 1 == 0 else percentage
            except ZeroDivisionError:
                percentage = 0

            lines.append(f"{vote.option.value}: {vote.count} **{percentage}%**")

            if vote.option == SimpleVote.Option.yes and percentage == 100:
                if self.is_selfie_vote():
                    if self.assign_selfie_role():
                        embed.set_footer(text = "Selfie role assigned.")

        embed.description = "\n".join(lines)
        asyncio.gather(channel.send(embed = embed))

