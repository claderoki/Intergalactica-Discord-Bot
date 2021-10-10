import asyncio
import datetime
import random
import re
from enum import Enum

import discord
from discord.ext import commands, tasks
from dateutil.relativedelta import relativedelta

from src.discord.cogs.custom.shared.helpers.helpers import ChannelHelper
from src.discord.helpers.known_guilds import KnownGuild
import src.config as config
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers.checks import specific_guild_only
from src.discord.helpers.utility import get_context_embed
from src.models import (Earthling, Human, Item,
                        TemporaryVoiceChannel, TemporaryTextChannel, database)
from src.discord.cogs.custom.shared.helpers.simple_poll import SimplePoll

class MaliciousAction(Enum):
    blacklisted_word = 1
    invite_url       = 2
    spam             = 3

    @property
    def ban_reason(self):
        if self == self.blacklisted_word:
            return "Using blacklisted word(s)"
        elif self == self.invite_url:
            return "Advertising"
        elif self == self.spam:
            return "Spam"

async def on_malicious_action(action : MaliciousAction, member : discord.Member, **kwargs):
    ban_if_new = False

    if action == MaliciousAction.blacklisted_word:
        message = kwargs["message"]
        words = kwargs["words"]

        embed = await get_context_embed(message, amount = 5)
        embed.color = discord.Color.red()
        embed.set_author(name = f"Blacklisted word(s) used by {member} ({member.id})", url = message.jump_url)

        lines = []
        lines.append(f"The following blacklisted word(s) were used")
        lines.append(", ".join([f"**{x}**" for x in words]))
        embed.description = "{}\n{}".format("\n".join(lines), embed.description)

        sendable = member.guild.get_channel(Intergalactica._channel_ids["c3po-log"])
        asyncio.gather(sendable.send(embed = embed))

        ban_if_new = True
    elif action == MaliciousAction.invite_url:
        try:
            await kwargs["message"].delete()
        except: pass
        ban_if_new = True
    elif action == MaliciousAction.spam:
        pass

    if ban_if_new:
        if MemberHelper.is_new(member):
            await member.ban(reason = action.ban_reason)

class Intergalactica(BaseCog):
    last_member_join = None

    _role_ids = {
        "selfies"   : 748566253534445568,
        "admin"     : 742243945693708381,
        "vc_access" : 761599311967420418,
        "5k+"       : 778744417322139689,
        "bumper"    : 780001849335742476,
        "age"       : {"18-20": 748606669902053387, "21-24": 748606823229030500, "25-29": 748606893387153448, "30+": 748606902363095206},
        "gender"    : {"male": 742301620062388226, "female": 742301646004027472, "other" : 742301672918745141},
        "ranks"     : {
            "luna"      : 748494880229163021,
            "nova"      : 748494888844132442,
            "aurora"    : 748494890127851521,
            "aquila"    : 748494890169794621,
            "orion"     : 748494891419697152,
            "andromeda" : 748494891751047183
        },
    }

    _channel_ids = {
        "general"        : 744650481682481233,
        "roles"          : 742303560988885044,
        "welcome"        : 742187165659693076,
        "warns"          : 777888951523606548,
        "selfies"        : 744703465086779393,
        "concerns"       : 863775516998107186,
        "staff_votes"    : 863775839945621534,
        "staff_chat"     : 863774968848449546,
        "bot_spam"       : 742163352712642600,
        "bot_commands"   : 863775558977323008,
        "introductions"  : 742567349613232249,
        "logs"           : 863775748400349214,
        "c3po-log"       : 863775783940390912,
    }

    async def get_invites(self, message):
        if "cdn" in message:
            return None

        regex = re.compile(r'discord(?:app|\.gg)/(?:invite/)?([a-zA-Z0-9\-]{2,32})')
        invite_urls = regex.findall(message)
        if len(invite_urls) == 0:
            return None

        invites = []
        for url in invite_urls:
            try:
                invite = await self.bot.fetch_invite(url)
            except discord.errors.NotFound:
                continue
            else:
                invites.append(invite)
        return invites

    def get_channel(self, name):
        return self.bot.get_channel(self._channel_ids[name])

    def __init__(self, bot):
        super().__init__(bot)
        self.welcome_messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        SimplePoll.add_guild_data(KnownGuild.intergalactica, self._channel_ids["staff_votes"], self._channel_ids["staff_chat"])

        guild = self.bot.get_guild(KnownGuild.intergalactica)
        self.role_needed_for_selfie_vote = guild.get_role(self._role_ids["ranks"]["nova"])

        self.start_task(self.illegal_member_purger,             check = self.bot.production)
        self.start_task(self.introduction_purger,               check = self.bot.production)
        self.start_task(self.temp_vc_poller,                    check = self.bot.production)
        self.start_task(self.mouse_role_cleanup,                check = self.bot.production)
        await asyncio.sleep( (60 * 60) * 3 )
        self.start_task(self.birthday_poller,                   check = self.bot.production)

    def on_milkyway_purchased(self, channel, member, amount):
        with database.connection_context():
            item = Item.get(code = "milky_way")
            human = self.bot.get_human(user = member)
            human.add_item(item, amount)

        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.description = f"Good job in purchasing {amount} milky way(s).\nInstructions:\n`/milkyway create` or `/milkyway extend #channel`"
        asyncio.gather(channel.send(embed = embed))

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if guild.id != KnownGuild.intergalactica:
            return
        if not self.bot.production:
            return

        await asyncio.sleep(5)

        found = False
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                found = True
                break
        if not found:
            entry = None

        channel = guild.get_channel(744668640309280840)
        embed = discord.Embed(color = discord.Color.red())
        embed.title = "ban"
        lines = []
        lines.append(f"**Offender:** {user} {user.mention}")
        if found:
            lines.append(f"**Reason:** {entry.reason}")
            lines.append(f"**Responsible moderator:** {entry.user}")

        embed.description = "\n".join(lines)
        await channel.send(embed = embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if SimplePoll.is_eligible(payload):
            poll = await SimplePoll.from_payload(payload)
            if poll.should_finish():
                poll.finish()

    def blacklisted_words_used(self, text):
        blacklisted_words = ["retard", "nigger", "fag"]

        words_used = []
        for word in blacklisted_words:
            if word in text:
                words_used.append(word)

        return words_used

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return
        if message.guild is None:
            return

        guild_data = SimplePoll.guild_data.get(message.guild.id)
        if guild_data is not None and guild_data["vote_channel"] == message.channel.id:
            coros = [message.add_reaction(x) for x in SimplePoll.options]
            asyncio.gather(*coros)
            return

        if message.guild.id != KnownGuild.intergalactica:
            return

        words = self.blacklisted_words_used(message.content.lower())
        if len(words) > 0:
            await on_malicious_action(MaliciousAction.blacklisted_word, message.author, message = message, words = words)

        invites = await self.get_invites(message.content)
        if invites:
            for invite in invites:
                if invite.guild.id != message.guild.id:
                    await on_malicious_action(MaliciousAction.invite_url, message.author, message = message)
            return

        if message.channel.id == self._channel_ids["general"]:
            if self.last_member_join is not None and "welcome" in message.content.lower():
                time_here = relativedelta(datetime.datetime.utcnow(), self.last_member_join)
                if time_here.minutes <= 5:
                    emoji = random.choice(("💛", "🧡", "🤍", "💙", "🖤", "💜", "💚", "❤️"))
                    asyncio.gather(message.add_reaction(emoji))
            elif random.randint(0, 1000) == 1:
                asyncio.gather(message.add_reaction("🤏"))

        if message.author.id == 172002275412279296: # tatsu
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                if embed.title == "Purchase Successful!":
                    field = embed.fields[0]
                    if field.name == "You Bought" and "milky way" in field.value.lower():
                        member_name = embed.footer.text.replace(" bought an item!", "")
                        class FakeCtx:
                            pass
                        ctx = FakeCtx()
                        ctx.bot = self.bot
                        ctx.guild = message.guild
                        member = await commands.MemberConverter().convert(ctx, member_name)

                        amount = int(field.value.split("`")[1])
                        self.on_milkyway_purchased(message.channel, member, amount)
                        return await message.delete()

    async def log(self, channel_name, content = None, **kwargs):
        channel = self.get_channel(channel_name)
        await channel.send(content = content, **kwargs)

    @commands.command(name = "vcchannel")
    @specific_guild_only(KnownGuild.intergalactica)
    @commands.has_role(_role_ids["5k+"])
    async def vc_channel(self, ctx, *args):
        name = " ".join(args) if len(args) > 0 else None

        category = None
        for category in ctx.guild.categories:
            if category.id == 742146159711092759:
                break
        channel = await category.create_voice_channel(name or "Temporary voice channel", reason = f"Requested by {ctx.author}")
        TemporaryVoiceChannel.create(guild_id = ctx.guild.id, channel_id = channel.id)
        await ctx.success()

    @commands.command(name = "textchannel")
    @specific_guild_only(KnownGuild.intergalactica)
    @commands.has_role(_role_ids["5k+"])
    async def text_channel(self, ctx, *args):

        category = None
        for category in ctx.guild.categories:
            if category.id == 742146159711092759:
                break
        if category is None:
            raise SendableException(ctx.translate("wtf_wrong_with_category"))

        voice = ctx.author.voice
        if voice is None:
            raise SendableException(ctx.translate("not_in_voice_channel"))

        vc = TemporaryVoiceChannel.select(TemporaryVoiceChannel.id)\
            .where(TemporaryVoiceChannel.channel_id == voice.channel.id)\
            .first()

        if vc is None:
            raise SendableException(ctx.translate("not_in_a_temp_vc"))

        if TemporaryTextChannel.select().where(TemporaryTextChannel.temp_vc == vc.id).count() > 0:
            raise SendableException(ctx.translate("already_exists"))

        channel = await category.create_text_channel(voice.channel.name, reason = f"Requested by {ctx.author}")

        TemporaryTextChannel.create(temp_vc = vc, channel_id = channel.id, guild_id = ctx.guild.id)

        await ctx.success()

    @commands.has_guild_permissions(administrator = True)
    @specific_guild_only(KnownGuild.intergalactica)
    @commands.command()
    async def warn(self, ctx, member : discord.Member, *, reason):
        await member.send(f"Hello {member}, this is an official warning. Reason: **{reason}**. Please be more careful in the future.")
        channel = self.get_channel("warns")
        await channel.send(f"Warned {member} for {reason}")

    @commands.has_guild_permissions(administrator = True)
    @specific_guild_only(KnownGuild.intergalactica)
    @commands.command()
    async def selfies(self, ctx):
        members = []

        rank_ids = [x for x in self._role_ids["ranks"].values() if x != self._role_ids["ranks"]["luna"]]

        for member in ctx.guild.members:
            has_selfie_role = False
            has_more_than_10k_role = False
            for role in member.roles:
                if role.id == self._role_ids["selfies"]:
                    has_selfie_role = True
                if role.id in rank_ids:
                    has_more_than_10k_role = True
            if not has_selfie_role and has_more_than_10k_role:
                members.append(member)

        await ctx.send("\n".join([str(x) for x in members]))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.production:
            return

        if member.guild.id == KnownGuild.mouse:
            role    = member.guild.get_role(841072184953012275)
            general = member.guild.get_channel(729909438378541116)
            message = await general.send(f"Welcome to the server {member.mention}, {role.mention} say hello!")
            self.welcome_messages[member.id] = message
        elif member.guild.id == KnownGuild.intergalactica:
            welcome_channel = self.get_channel("welcome")
            text = self.bot.translate("member_join")

            embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
            embed.description = text.format(member = member)

            asyncio.gather(welcome_channel.send(embed = embed))

            self.last_member_join = datetime.datetime.utcnow()
            if random.randint(0, 250) == 0:
                text = f"Hello and Welcome {member.mention}! My name is C-3PO and I’ll be around to assist you with anything you may need during your stay. I have prepared a fresh pigeon for you and can share many interesting facts about our server. I hope you enjoy your stay and I hope you have a wonderful evening."
            else:
                text = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
            message = await self.get_channel("general").send(text)
            self.welcome_messages[member.id] = message

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.production:
            return

        try:
            await self.welcome_messages[member.id].delete()
        except:
            pass

        if member.guild.id != KnownGuild.intergalactica:
            return

        welcome_channel = self.get_channel("welcome")
        text = self.bot.translate("member_leave")

        embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

    async def on_rank(self, member, role):
        role_to_add = member.guild.get_role(self._role_ids["5k+"])
        asyncio.gather(member.add_roles(role_to_add))

        if role == self.role_needed_for_selfie_vote:
            if member.guild.get_role(self._role_ids["selfies"]) not in member.roles:
                channel = self.get_channel("staff_votes")
                asyncio.gather(channel.send(f"Should {member.mention} (**{member}**) get selfie access?"))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not self.bot.production:
            return
        if after.guild.id != KnownGuild.intergalactica:
            return
        if len(after.roles) <= len(before.roles):
            return

        added_role = None

        for role in after.roles:
            if role not in before.roles:
                added_role = role
                break

        for _, rank_id in self._role_ids["ranks"].items():
            if added_role.id == rank_id:
                await self.on_rank(after, added_role)

    @tasks.loop(minutes = 5)
    async def temp_vc_poller(self):
        with database.connection_context():
            for temporary_voice_channel in TemporaryVoiceChannel:
                channel = temporary_voice_channel.channel
                if channel is None or len(channel.members) == 0:
                    query = TemporaryTextChannel.select()
                    query = query.where(TemporaryTextChannel.temp_vc == temporary_voice_channel)

                    for temporary_text_channel in query:
                        temporary_text_channel.delete_instance()
                    temporary_voice_channel.delete_instance()

    @tasks.loop(minutes = 20)
    async def introduction_purger(self):
        channels = []
        channels.append(self.get_channel("introductions"))
        channels.append(self.bot.get_channel(729909501578182747))
        channels.append(self.bot.get_channel(841049839466053693))

        for channel in channels:
            await ChannelHelper.cleanup_channel(channel)

    @tasks.loop(hours = 5)
    async def mouse_role_cleanup(self):
        guild = self.bot.get_guild(KnownGuild.mouse)
        new_role = guild.get_role(764586989466943549)

        for member in guild.members:
            time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
            more_than_week = time_here.weeks >= 1 or time_here.months > 1 or time_here.years >= 1
            if more_than_week and new_role in member.roles:
                await member.remove_roles(new_role)

    @tasks.loop(hours = 1)
    async def illegal_member_purger(self):
        for guild in self.bot.guilds:
            if guild.id not in (KnownGuild.mouse, KnownGuild.intergalactica):
                continue

            for member in guild.members:
                if member.bot:
                    continue

                if not MemberHelper.has_mandatory_roles(member):
                    time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
                    if time_here.hours >= 6:
                        asyncio.gather(member.kick(reason = "Missing mandatory role(s)"))

    @tasks.loop(hours = 12)
    async def birthday_poller(self):
        now = datetime.datetime.utcnow()

        query = Human.select()
        query = query.join(Earthling, on = (Human.id == Earthling.human))
        query = query.where(Earthling.guild_id == KnownGuild.intergalactica)
        query = query.where(Human.date_of_birth != None)
        query = query.where(Human.date_of_birth.month == now.month)
        query = query.where(Human.date_of_birth.day == now.day)
        query = query.order_by(Human.date_of_birth.asc())

        with database.connection_context():
            for human in query:
                await self.log("c3po-log", f"**{human.user}** {human.mention} Should be celebrating their birthday today.")

class MemberHelper:
    __slots__ = ()

    @classmethod
    def _has_mandatory_roles_mouse(cls, member) -> bool:
        role = member.guild.get_role(729913735946305548)
        if role is None:
            return True
        return role in member.roles

    @classmethod
    def _has_mandatory_roles_intergalactica(cls, member) -> bool:
        age_roles = [member.guild.get_role(x).id for x in Intergalactica._role_ids["age"].values()]
        gender_roles = [member.guild.get_role(x).id for x in Intergalactica._role_ids["gender"].values()]

        has_age_role = False
        has_gender_role = False

        for role in member.roles:
            if role.id in age_roles:
                has_age_role = True
            elif role.id in gender_roles:
                has_gender_role = True

        return has_age_role and has_gender_role

    @classmethod
    def has_mandatory_roles(cls, member) -> bool:
        if member.guild.id == KnownGuild.intergalactica:
            return cls._has_mandatory_roles_intergalactica(member)
        elif member.guild.id == KnownGuild.mouse:
            return cls._has_mandatory_roles_mouse(member)
        else:
            return True

    @classmethod
    def is_new(cls, member) -> bool:
        if member.guild.id == KnownGuild.intergalactica:
            for role in member.roles:
                if role.id == cls._role_ids["vc_access"]:
                    return False
                if role.id == cls._role_ids["5k+"]:
                    return False
                return True

        return False

def setup(bot):
    bot.add_cog(Intergalactica(bot))
