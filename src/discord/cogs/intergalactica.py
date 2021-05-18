import asyncio
import datetime
import random
import re
from enum import Enum

import discord
from discord.ext import commands, tasks

from dateutil.relativedelta import relativedelta
import src.config as config
from src.discord.cogs.core import BaseCog
from src.discord.errors.base import SendableException
from src.discord.helpers.checks import specific_guild_only
from src.discord.helpers.embed import Embed
from src.discord.helpers.utility import get_context_embed
from src.discord.helpers.waiters import MemberWaiter
from src.models import (Earthling, Human, Item, RedditAdvertisement, Reminder,
                        TemporaryVoiceChannel, database)



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
        if Intergalactica.member_is_new(member):
            await member.ban(reason = action.ban_reason)

guild_id       = 742146159711092757
mouse_guild_id = 729843647347949638

class Intergalactica(BaseCog):
    last_member_join = None

    vote_emojis = ("✅", "❎", "❓")
    guild_id = guild_id
    mouse_guild_id = mouse_guild_id
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
        "warns"          : 777888951523606548,
        "selfies"        : 744703465086779393,
        "concerns"       : 758296826549108746,
        "staff_votes"    : 795644055979294720,
        "staff_chat"     : 796413284105453589,
        "bot_spam"       : 742163352712642600,
        "bot_commands"   : 796413360706682933,
        "introductions"  : 742567349613232249,
        "tabs"           : 757961433911787592,
        "logs"           : 796438050091171870,
        "c3po-log"       : 817078062784708608,
    }

    async def get_invites(self, message):
        regex = re.compile(r'discord(?:\.com|app\.com|\.gg)/(?:invite/)?([a-zA-Z0-9\-]{2,32})')
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
        self.guild = self.bot.get_guild(self.guild_id)
        self.bump_available = datetime.datetime.utcnow() + datetime.timedelta(minutes = 120)
        self.role_needed_for_selfie_vote = self.guild.get_role(self._role_ids["ranks"]["nova"])

        self.start_task(self.reddit_advertiser,                 check = self.bot.production)
        self.start_task(self.illegal_member_purger,             check = self.bot.production)
        self.start_task(self.introduction_purger,               check = self.bot.production)
        self.start_task(self.temp_vc_poller,                    check = self.bot.production)
        self.start_task(self.disboard_bump_available_notifier,  check = self.bot.production)
        self.start_task(self.reminder_notifier,                 check = self.bot.production)
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
        if guild.id != self.guild_id:
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

    @classmethod
    def member_is_new(cls, member):
        for role in member.roles:
            if role.id == cls._role_ids["vc_access"]:
                return False
            if role.id == cls._role_ids["5k+"]:
                return False
        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not self.bot.production:
            return
        if payload.guild_id != self.guild_id:
            return
        if payload.member is None or payload.member.bot:
            return
        if payload.channel_id != self._channel_ids["staff_votes"]:
            return

        is_skip_vote = lambda x : x == self.vote_emojis[-1]

        if str(payload.emoji) in self.vote_emojis:
            def clean_value(value):
                return int(value) if value % 1 == 0 else round(value, 2)
            channel = self.bot.get_channel(payload.channel_id)
            staff_members = [x for x in channel.members if not x.bot]
            message = await channel.fetch_message(payload.message_id)

            reactions = [x for x in message.reactions if str(x.emoji) in self.vote_emojis]
            all_user_ids = set()
            votes = {}
            skipped_member_count = 0

            for reaction in reactions:
                users = await reaction.users().flatten()
                valid_users = [x for x in users if not x.bot and not x.id in all_user_ids]
                if is_skip_vote(str(reaction.emoji)):
                    skipped_member_count = len(valid_users)

                votes[str(reaction.emoji)] = len(valid_users)

                for user in users:
                    if not user.bot:
                        all_user_ids.add(user.id)

            if len(all_user_ids) == len(staff_members):
                embed = discord.Embed(color = self.bot.get_dominant_color(None))
                lines = []
                lines.append("*(all staff members finished voting)*")
                lines.append(message.content)
                lines.append("")

                for vote, vote_count in votes.items():
                    if not is_skip_vote(vote):
                        total_votes = (len(staff_members)-skipped_member_count)
                        try:
                            percentage = (vote_count/total_votes)*100
                        except ZeroDivisionError:
                            percentage = 0

                        cleaned_value = clean_value(percentage)
                        lines.append(f"{vote}: {vote_count} **{cleaned_value}%**")
                        if vote == self.vote_emojis[0] and vote_count == len(staff_members):
                            if "selfie access" in message.content.lower() or "selfie perm" in message.content.lower():
                                user_id = MemberWaiter.get_id(message.content)
                                member = message.guild.get_member(user_id)
                                if member is not None:
                                    selfie_role = message.guild.get_role(self._role_ids["selfies"])
                                    await member.add_roles(selfie_role)
                                    embed.set_footer(text = "Selfie role assigned.")

                embed.description = "\n".join(lines)
                asyncio.gather(self.get_channel("staff_chat").send(embed = embed))

    def blacklisted_words_used(self, text):
        blacklisted_words = ["retard", "nigger"]

        words_used = []
        for word in blacklisted_words:
            if word in text:
                words_used.append(word)

        return words_used

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return
        if message.guild is not None and message.guild.id != self.guild_id:
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

        if message.channel.id == self._channel_ids["staff_votes"]:
            coros = [message.add_reaction(x) for x in self.vote_emojis]
            asyncio.gather(*coros)

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

        if message.content and message.content.lower() == "!d bump":
            disboard_response = await self.bot.wait_for("message", check = lambda x : x.author.id == 302050872383242240 and x.channel.id == message.channel.id)
            embed = disboard_response.embeds[0]
            text = embed.description
            minutes = None
            if "minutes until the server can be bumped" in text:
                minutes = int([x for x in text.split() if x.isdigit()][0])
            else:
                minutes = 120

            if minutes is  not None:
                self.bump_available = datetime.datetime.utcnow() + datetime.timedelta(minutes = minutes)

    async def log(self, channel_name, content = None, **kwargs):
        channel = self.get_channel(channel_name)
        await channel.send(content = content, **kwargs)

    async def on_member_leave_or_join(self, member, type):
        if not self.bot.production or member.guild.id != self.guild_id:
            return

        welcome_channel = member.guild.system_channel
        text = self.bot.translate("member_" + type)

        embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

        if type == "join":
            self.last_member_join = datetime.datetime.utcnow()
            text = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
            message = await self.get_channel("general").send(text)
            self.welcome_messages[member.id] = message
        elif type == "leave" and member.id in self.welcome_messages:
            try:
                await self.welcome_messages[member.id].delete()
            except:
                pass

    @commands.command(name = "vcchannel")
    @specific_guild_only(guild_id)
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

    @commands.has_guild_permissions(administrator = True)
    @specific_guild_only(guild_id)
    @commands.command()
    async def warn(self, ctx, member : discord.Member, *, reason):
        await member.send(f"Hello {member}, this is an official warning. Reason: **{reason}**. Please be more careful in the future.")
        channel = self.get_channel("warns")
        await channel.send(f"Warned {member} for {reason}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.production:
            return

        if member.guild.id == mouse_guild_id:
            role    = member.guild.get_role(841072184953012275)
            general = member.guild.get_channel(729909438378541116)
            await general.send(f"Welcome to the server ({member.mention}), {role.mention} say hello!")

        if member.guild.id != self.guild_id:
            return

        welcome_channel = member.guild.system_channel
        text = self.bot.translate("member_join")

        embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

        self.last_member_join = datetime.datetime.utcnow()
        text = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
        message = await self.get_channel("general").send(text)
        self.welcome_messages[member.id] = message

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.production or member.guild.id != self.guild_id:
            return

        welcome_channel = member.guild.system_channel
        text = self.bot.translate("member_leave")

        embed = discord.Embed(color = self.bot.get_dominant_color(member.guild))
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

        try:
            await self.welcome_messages[member.id].delete()
        except:
            pass

    async def on_rank(self, member, role):
        role_to_add = self.guild.get_role(self._role_ids["5k+"])
        asyncio.gather(member.add_roles(role_to_add))

        if role == self.role_needed_for_selfie_vote:
            if member.guild.get_role(self._role_ids["selfies"]) not in member.roles:
                channel = self.get_channel("staff_votes")
                asyncio.gather(channel.send(f"Should {member.mention} (**{member}**) get selfie access?"))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not self.bot.production:
            return
        if after.guild.id != self.guild_id:
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

    @tasks.loop(hours = 1)
    async def reddit_advertiser(self):
        query = RedditAdvertisement.select()
        query = query.where(RedditAdvertisement.guild_id == self.guild.id)

        for reddit_advertisement in query:
            if reddit_advertisement.available:
                embed = Embed.success(None)
                submissions = await reddit_advertisement.advertise()
                embed.set_author(name = "bump_successful", url = submissions[0].shortlink)
                asyncio.gather(self.log("c3po-log", embed = embed))

                await asyncio.sleep(10)
                for submission in submissions:
                    submission.mod.sfw()

    @tasks.loop(minutes = 1)
    async def disboard_bump_available_notifier(self):
        if self.bump_available <= datetime.datetime.utcnow():
            bot_spam = self.get_channel("bot_spam")
            last_message = bot_spam.last_message
            content = "A bump is available! `!d bump` to bump."

            if last_message is None or last_message.content != content:
                await bot_spam.send(content)

    @tasks.loop(minutes = 5)
    async def temp_vc_poller(self):
        with database.connection_context():
            for temporary_voice_channel in TemporaryVoiceChannel:
                channel = temporary_voice_channel.channel
                if channel is None or len(channel.members) == 0:
                    temporary_voice_channel.delete_instance()

    @tasks.loop(minutes = 20)
    async def introduction_purger(self):
        channels = []
        channels.append(self.get_channel("introductions"))
        channels.append(self.bot.get_channel(729909501578182747))
        channels.append(self.bot.get_channel(841049839466053693))

        for channel in channels:
            await ChannelHelper.cleanup_channel(channel)

    @tasks.loop(seconds = 30)
    async def reminder_notifier(self):
        query = Reminder.select()
        query = query.where(Reminder.finished == False)
        query = query.where(Reminder.due_date <= datetime.datetime.utcnow())

        for reminder in query:
            sendable = reminder.sendable
            if sendable is not None:
                embed = discord.Embed(color = self.bot.get_dominant_color(None))
                embed.set_author(name = "Reminder", icon_url = "https://cdn.discordapp.com/attachments/744172199770062899/804862458070040616/1.webp")
                embed.description = reminder.text
                asyncio.gather(sendable.send(content = f"<@{reminder.user_id}>", embed = embed))

            reminder.finished = True
            reminder.save()

    @tasks.loop(hours = 1)
    async def illegal_member_purger(self):
        for guild in self.bot.guilds:
            if guild.id not in (self.mouse_guild_id, self.guild_id):
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
        query = query.where(Earthling.guild_id == self.guild.id)
        query = query.where(Human.date_of_birth != None)
        query = query.where(Human.date_of_birth.month == now.month)
        query = query.where(Human.date_of_birth.day == now.day)
        query = query.order_by(Human.date_of_birth.asc())

        with database.connection_context():
            for human in query:
                await self.log("c3po-log", f"**{human.user}** {human.mention} Should be celebrating their birthday today.")

class ChannelHelper:
    __slots__ = ()

    @classmethod
    async def cleanup_channel(cls, channel: discord.TextChannel, log_channel: discord.TextChannel = None):
        """Clears messages from users no longer in the guild."""
        tasks = []
        total_messages = 0
        messages_to_remove = []
        async for introduction in channel.history(limit=200):
            if isinstance(introduction.author, discord.User):
                messages_to_remove.append(introduction)
            total_messages += 1

        if len(messages_to_remove) >= (total_messages//2):
            return
        for introduction in messages_to_remove:
            if log_channel is not None:
                embed = discord.Embed(
                    color = config.bot.get_dominant_color(),
                    title = f"Purged: Introduction by {introduction.author}",
                    description = introduction.content
                )
                tasks.append(log_channel.send(embed = embed))
            tasks.append(introduction.delete())

        asyncio.gather(*tasks)

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
        if member.guild.id == Intergalactica.guild_id:
            return cls._has_mandatory_roles_intergalactica(member)
        elif member.guild.id == Intergalactica.mouse_guild_id:
            return cls._has_mandatory_roles_mouse(member)
        else:
            return True

    @classmethod
    def is_new(cls, member) -> bool:
        if member.guild.id == guild_id:
            for role in member.roles:
                if role.id == cls._role_ids["vc_access"]:
                    return False
                if role.id == cls._role_ids["5k+"]:
                    return False
                return True

        return False

def setup(bot):
    bot.add_cog(Intergalactica(bot))
