import asyncio
import datetime
import typing
import re

from emoji import emojize, demojize
import discord
from discord.ext import commands, tasks
from dateutil.relativedelta import relativedelta

from src.discord.errors.base import SendableException
from src.discord.helpers.embed import Embed
from src.models import Poll, PollTemplate, Option, Reminder, Settings, Item, NamedEmbed, Human, Earthling, TemporaryVoiceChannel, TemporaryChannel, HumanItem, RedditAdvertisement, database
from src.discord.helpers.waiters import IntWaiter
import src.discord.helpers.pretty as pretty

def is_intergalactica():
    def predicate(ctx):
        return ctx.guild and ctx.guild.id == Intergalactica.guild_id
    return commands.check(predicate)

class Intergalactica(commands.Cog):
    vote_emojis = ("✅", "❎")
    guild_id = 742146159711092757

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
        "selfies"        : 744703465086779393,
        "concerns"       : 758296826549108746,
        "staff_votes"    : 795644055979294720,
        "staff_chat"     : 796413284105453589,
        "bot_spam"       : 742163352712642600,
        "bot_commands"   : 796413360706682933,
        "introductions"  : 742567349613232249,
        "tabs"           : 757961433911787592,
        "logs"           : 796438050091171870
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
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)
        self.bot.get_dominant_color(self.guild)
        self.bump_available = datetime.datetime.utcnow() + datetime.timedelta(minutes = 120)
        self.role_needed_for_selfie_vote = self.guild.get_role(self._role_ids["ranks"]["nova"])

        self.reminder_notifier.start()

        if self.bot.production:
            self.reddit_advertiser.start()
            self.illegal_member_notifier.start()
            self.temp_vc_poller.start()
            self.temp_channel_checker.start()
            self.disboard_bump_available_notifier.start()
            self.introduction_purger.start()
            await asyncio.sleep( (60 * 60) * 3 )
            self.birthday_poller.start()

    def on_milkyway_purchased(self, channel, member, amount):
        with database.connection_context():
            item = Item.get(name = "Milky way")
            human, _ = Human.get_or_create(user_id = member.id)
            human.add_item(item, amount)

        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.description = f"Good job in purchasing {amount} milky way(s).\nInstructions:\n`/milkyway create` or `/milkyway extend #channel`"
        asyncio.gather(channel.send(embed = embed))

    def member_is_new(self, member):
        for role in member.roles:
            if role.id == self._role_ids["vc_access"]:
                return False
            if role.id == self._role_ids["5k+"]:
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

        if str(payload.emoji) in self.vote_emojis:
            def clean_value(value):
                return int(value) if value % 1 == 0 else round(value, 2)
            channel = self.bot.get_channel(payload.channel_id)
            staff_members = [x for x in channel.members if not x.bot]
            message = await channel.fetch_message(payload.message_id)

            positive, negative = [x for x in message.reactions if str(x.emoji) in self.vote_emojis]
            positive_users = [x for x in await positive.users().flatten() if not x.bot]
            negative_users = [x for x in await negative.users().flatten() if not x.bot and x not in positive_users]
            if len(positive_users)+len(negative_users) == len(staff_members):
                embed = discord.Embed(color = self.bot.get_dominant_color(None))
                lines = []
                lines.append("*(all staff members finished voting)*")
                lines.append(message.content)
                lines.append("")
                lines.append(f"{self.vote_emojis[0]}: {len(positive_users)} **{clean_value(len(positive_users)/len(staff_members)*100)}%**")
                lines.append(f"{self.vote_emojis[1]}: {len(negative_users)} **{clean_value(len(negative_users)/len(staff_members)*100)}%**")
                embed.description = "\n".join(lines)
                asyncio.gather(self.get_channel("staff_chat").send(embed = embed))

    def blacklisted_words_used(self, text):
        blacklisted_words = ["retard"]

        words_used = []
        for word in blacklisted_words:
            if word in text:
                words_used.append(word)

        return words_used

    async def blacklisted_action(self, message, words):
        embed = discord.Embed(color = discord.Color.red())
        embed.set_author(name = f"Blacklisted word(s) used by {message.author} ({message.author.id})", url = message.jump_url)

        lines = []
        lines.append(f"The following blacklisted word(s) were used")
        lines.append(", ".join([f"**{x}**" for x in words]))
        lines.append("\n**Context:**")

        messages = []
        async for msg in message.channel.history(limit = 5, before = message):
            messages.append(msg)
        messages.append(message)

        last_author = None
        fields = []
        for msg in messages:
            content = msg.content

            if not content:
                if len(msg.embeds) > 0:
                    content = "[embed]"
                if len(msg.attachments) > 0:
                    content = "[attachment(s)]"

            if last_author is not None and last_author.id == msg.author.id:
                fields[-1]["value"] += f"\n{content}"
            else:
                fields.append({"name": str(msg.author), "value": content})

            last_author = msg.author

        for field in fields:
            embed.add_field(**field, inline = False)

        embed.description = "\n".join(lines)

        # sendable = self.bot.owner
        sendable = self.get_channel("staff_chat")
        await sendable.send(embed = embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return
        if message.guild is not None and message.guild.id != self.guild_id:
            return

        words = self.blacklisted_words_used(message.content)
        if len(words) > 0:
            await self.blacklisted_action(message, words)

        invites = await self.get_invites(message.content)
        if invites:
            asyncio.gather(message.delete())
            for invite in invites:
                if invite.guild.id != message.guild.id:
                    if self.member_is_new(message.author):
                        await message.author.ban(reason = "Advertising")
            return

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
                        return asyncio.gather(message.delete())

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
        if type == "join":
            name = f"Welcome to {member.guild.name}!"
        else:
            name = "Farewell, Earthling."
        embed.set_author(name = name, icon_url = "https://cdn.discordapp.com/attachments/744172199770062899/768460504649695282/c3p0.png")
        embed.description = text.format(member = member)

        asyncio.gather(welcome_channel.send(embed = embed))

        if type == "join":
            msg = f"Welcome {member.mention}! Make sure to pick some <#{self._channel_ids['roles']}> and make an <#{self._channel_ids['introductions']}>"
            asyncio.gather(self.get_channel("general").send(msg))

    async def create_selfie_poll(self, ctx, member):
        poll = Poll.from_template(PollTemplate.get(name = "selfies"))
        poll.question = f"Should {member} be given selfie access?"
        poll.author_id = ctx.author.id
        poll.save()
        poll.create_options(("Yes", "No", "Idk them well enough yet"))
        await poll.send()
        poll.save()
        return poll

    @commands.command(name = "vcchannel")
    @is_intergalactica()
    @commands.has_role(_role_ids["5k+"])
    async def vc_channel(self, ctx, *args):
        name = " ".join(args) if len(args) > 0 else None

        for category in ctx.guild.categories:
            if category.id == 742146159711092759:
                break
        channel = await category.create_voice_channel(name or "Temporary voice channel", reason = f"Requested by {ctx.author}")
        vc = TemporaryVoiceChannel.create(guild_id = ctx.guild.id, channel_id = channel.id)
        await ctx.success()

    @commands.command()
    @is_intergalactica()
    @commands.has_guild_permissions(administrator = True)
    async def bump(self, ctx):
        try:
            reddit_advertisement = RedditAdvertisement.get(guild_id = ctx.guild.id)
        except RedditAdvertisement.DoesNotExist:
            return

        if not reddit_advertisement.available:
            embed = Embed.error(None)
            embed.set_footer(text = ctx.translate("available_again_at"))
            embed.timestamp = reddit_advertisement.last_advertised + datetime.timedelta(hours = 24)
            asyncio.gather(ctx.send(embed = embed))
        else:
            embed = Embed.success(None)
            submissions = await reddit_advertisement.advertise()
            embed.set_author(name = ctx.translate("bump_successful"), url = submissions[0].shortlink)
            asyncio.gather(ctx.send(embed = embed))

            await asyncio.sleep(10)
            for submission in submissions:
                submission.mod.sfw()


    @commands.command()
    @is_intergalactica()
    async def bumper(self, ctx):
        role = ctx.guild.get_role(780001849335742476)

        for _role in ctx.author.roles:
            if _role == role:
                asyncio.gather(ctx.send("The bumper role has been removed."))
                return asyncio.gather(ctx.author.remove_roles(role))

        asyncio.gather(ctx.send("The bumper role has been added."))
        asyncio.gather(ctx.author.add_roles(role))

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def selfiepoll(self, ctx, member : discord.Member):
        await self.create_selfie_poll(ctx, member)
        await ctx.success()

    def get_milkyway_human_item(self, user):
        human_item = HumanItem.get_or_none(
            human = Human.get_or_create(user_id = user.id)[0],
            item = Item.get(code = "milky_way")
        )
        if human_item is None or human_item.amount == 0:
            raise SendableException("no_milky_way")
        return human_item

    @commands.group()
    async def milkyway(self, ctx):
        pass

    @commands.has_guild_permissions(administrator = True)
    @milkyway.command(name = "accept")
    async def milkyway_accept(self, ctx, temp_channel : TemporaryChannel):
        if temp_channel.status != TemporaryChannel.Status.pending:
            raise SendableException(ctx.translate("temp_channel_not_pending"))
        if not temp_channel.active:
            raise SendableException(ctx.translate("temp_channel_not_active"))
        temp_channel.set_expiry_date(datetime.timedelta(days = 7 * temp_channel.pending_milky_ways))
        temp_channel.pending_milky_ways = 0
        await temp_channel.create_channel()
        temp_channel.status = TemporaryChannel.Status.accepted
        temp_channel.save()
        await temp_channel.user.send(f"Your request for a milkyway channel was accepted.")
        asyncio.gather(ctx.success())

    @commands.has_guild_permissions(administrator = True)
    @milkyway.command(name = "deny")
    async def milkyway_deny(self, ctx, temp_channel : TemporaryChannel, *, reason):
        if temp_channel.status != TemporaryChannel.Status.pending:
            raise SendableException(ctx.translate("temp_channel_not_pending"))
        if not temp_channel.active:
            raise SendableException(ctx.translate("temp_channel_not_active"))

        temp_channel.status = TemporaryChannel.Status.denied
        temp_channel.active = False
        temp_channel.deny_reason = reason
        human_item = self.get_milkyway_human_item(temp_channel.user)
        human_item.amount += temp_channel.pending_milky_ways
        human_item.save()
        temp_channel.save()
        await temp_channel.user.send(f"Your request for a milkyway channel was denied. Reason: `{temp_channel.deny_reason}`")
        asyncio.gather(ctx.success())

    @milkyway.command(name = "create")
    async def milkyway_create(self, ctx):
        human_item = self.get_milkyway_human_item(ctx.author)
        temp_channel = TemporaryChannel(guild_id = ctx.guild.id, user_id = ctx.author.id)

        if human_item.amount > 1:
            waiter = IntWaiter(ctx, prompt = ctx.translate("milky_way_count_prompt"), min = 1, max = human_item.amount)
            milky_ways_to_use = await waiter.wait()
        else:
            milky_ways_to_use = 1

        temp_channel.pending_milky_ways = milky_ways_to_use

        human_item.amount -= milky_ways_to_use
        human_item.save()

        await temp_channel.editor_for(ctx, "name")
        await temp_channel.editor_for(ctx, "topic")

        await ctx.send("A request has been sent to the staff.")

        temp_channel.save()
        await self.get_channel("bot_commands").send(embed = temp_channel.ticket_embed)

    @milkyway.command(name = "extend")
    async def milkyway_extend(self, ctx, channel : discord.TextChannel):
        human_item = self.get_milkyway_human_item(ctx.author)

        try:
            temp_channel = TemporaryChannel.get(channel_id = channel.id, guild_id = ctx.guild.id)
        except TemporaryChannel.DoesNotExist:
            raise SendableException(ctx.translate("temp_channel_not_found"))

        if human_item.amount > 1:
            waiter = IntWaiter(ctx, prompt = ctx.translate("milky_way_count_prompt"), min = 1, max = human_item.amount)
            milky_ways_to_use = await waiter.wait()
        else:
            milky_ways_to_use = 1

        temp_channel.set_expiry_date(datetime.timedelta(days = 7 * milky_ways_to_use ))
        asyncio.gather(temp_channel.update_channel_topic())
        human_item.amount -= milky_ways_to_use
        human_item.save()
        temp_channel.save()

        await ctx.send(f"Okay. This channel has been extended until `{temp_channel.expiry_date}`")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.on_member_leave_or_join(member, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.on_member_leave_or_join(member, "leave")

    async def on_rank(self, member, role):
        role = self.guild.get_role(self._role_ids["5k+"])
        asyncio.gather(member.add_roles(role))

        if role == self.role_needed_for_selfie_vote:
            if member.guild.get_role(self._role_ids["selfies"]) not in member:
                asyncio.gather(self.log("bot_commands", f"**{member}** {member.mention} has achieved the rank needed for selfies ({role.name})."))

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

        for rank_name, rank_id in self._role_ids["ranks"].items():
            if added_role.id == rank_id:
                await self.on_rank(after, added_role)

    def embed_from_name(self, name, indexes):
        with database.connection_context():
            named_embed = NamedEmbed.get(name = name)
        if indexes is not None:
            embed = named_embed.get_embed_only_selected_fields([x-1 for x in indexes])
        else:
            embed = named_embed.embed
        return embed

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    @is_intergalactica()
    async def ensure5k(self, ctx):
        encompassing_role = self.guild.get_role(self._role_ids["5k+"])
        rank_ids = list(self._role_ids["ranks"].values())
        for member in ctx.guild.members:
            has_rank_role = False
            has_encompassing_role = False
            for role in member.roles:
                if role.id in rank_ids:
                    has_rank_role = True
                if role.id == encompassing_role.id:
                    has_encompassing_role = True
            if has_rank_role and not has_encompassing_role:
                asyncio.gather(member.add_roles(encompassing_role))

    async def edit_personal_role(self, ctx, **kwargs):
        attr_name = ctx.command.name
        attr_value = kwargs[attr_name]

        if attr_name == "name":
            kwargs["color"] = ctx.guild_color
        elif attr_name == "color":
            kwargs["name"] = ctx.author.display_name

        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        new = earthling.personal_role_id is None or earthling.personal_role is None
        if new:
            first_earthling = Earthling.select().where(Earthling.personal_role_id != None).first()
            position = first_earthling.personal_role.position if first_earthling else 0
            role = await ctx.guild.create_role(**kwargs)
            await role.edit(position = position)
            earthling.personal_role = role
            earthling.save()
            await ctx.send(ctx.bot.translate("role_created").format(role = role))
        else:
            role = earthling.personal_role
            await role.edit(**{attr_name : attr_value})
            msg = ctx.bot.translate(f"attr_added").format(name = "role's " + attr_name, value = attr_value)
            embed = discord.Embed(color = role.color, title = msg)
            await ctx.send(embed = embed)

        await ctx.author.add_roles(role)

    @commands.group()
    @is_intergalactica()
    async def role(self, ctx):
        has_5k = ctx.guild.get_role(self._role_ids["5k+"]) in ctx.author.roles
        is_nitro_booster = ctx.author.premium_since is not None
        allowed = has_5k or is_nitro_booster

        if not allowed:
            raise SendableException("You are not allowed to run this command yet, needed: 5k+ XP or Nitro Booster")

    @role.command(name = "color", aliases = ["colour"])
    async def role_color(self, ctx, color : discord.Color = None):
        if ctx.author.id == 355186573119324161:
            return

        if color is None:
            color = self.bot.calculate_dominant_color(self.bot._get_icon_url(ctx.author))

        await self.edit_personal_role(ctx, color = color)

    @role.command(name = "name")
    async def role_name(self, ctx, *, name : str):
        await self.edit_personal_role(ctx, name = name)

    @commands.is_owner()
    @role.command(name = "list")
    async def role_list(self, ctx):
        query = Earthling.select()
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.where(Earthling.personal_role_id != None)
        roles = []
        for earthling in query:
            role = earthling.personal_role
            if role is None:
                earthling.personal_role_id = None
                earthling.save()
            else:
                roles.append(role)
        roles.sort(key = lambda x : x.position)

        table = pretty.Table()
        table.add_row(pretty.Row(["role", "pos", "in use"], header = True))

        for role in roles:
            values = [role.name, role.position, len(role.members) > 0]
            table.add_row(pretty.Row(values))
        await table.to_paginator(ctx, 20).wait()

        table = pretty.Table()

    @commands.is_owner()
    @role.command(name = "link")
    async def role_link(self, ctx, role : discord.Role):
        members = role.members

        if len(members) > 3:
            await ctx.send("Too many people have this role.")
        else:
            for member in role.members:
                human, _ = Earthling.get_or_create_for_member(ctx.author)
                human.personal_role_id = role.id
                human.save()

            await ctx.send(ctx.translate("roles_linked"))

    @role.command(name = "delete")
    async def delete_role(self, ctx):
        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        if earthling.personal_role_id is not None:
            role = earthling.personal_role
            if role is not None:
                await role.delete()

            earthling.personal_role_id = None
            earthling.save()

            await ctx.send(ctx.bot.translate("attr_removed").format(name = "role"))

    @role.command(name = "reset")
    @commands.is_owner()
    async def role_reset(self, ctx):
        roles_deleted = []
        for earthling in Earthling:
            if earthling.personal_role_id is not None:
                role = earthling.personal_role
                if role is not None and earthling.member is None:
                    roles_deleted.append(role.name)
                    asyncio.gather(role.delete())

        embed = self.bot.get_base_embed()
        if len(roles_deleted) > 0:
            embed.title = "The following roles were purged:"
            lines = "`\n`".join(roles_deleted)
            embed.description = f"`{lines}`"
        else:
            embed.description = "No roles needed purging."

        asyncio.gather(ctx.send(embed = embed))

    @commands.command(aliases = [ x.name for x in NamedEmbed.select(NamedEmbed.name).where(NamedEmbed.settings == 2) ])
    async def getembed(self, ctx, numbers : commands.Greedy[int] = None):
        embed = self.embed_from_name(ctx.invoked_with, numbers)
        await ctx.send(embed = embed)

    @tasks.loop(hours = 1)
    async def temp_channel_checker(self):
        with database.connection_context():
            query = TemporaryChannel.select()
            query = query.where(TemporaryChannel.active == True)
            query = query.where(TemporaryChannel.expiry_date != None)
            query = query.where(TemporaryChannel.expiry_date <= datetime.datetime.utcnow())
            for temp_channel in query:
                channel = temp_channel.channel
                temp_channel.active = False
                if channel is not None:
                    await channel.delete(reason = "Expired")
                temp_channel.channel_id = None
                temp_channel.save()

    @tasks.loop(hours = 1)
    async def reddit_advertiser(self):
        query = RedditAdvertisement.select()
        query = query.where(RedditAdvertisement.guild_id == self.guild.id)

        for reddit_advertisement in query:
            if reddit_advertisement.available:
                embed = Embed.success(None)
                submissions = await reddit_advertisement.advertise()
                embed.set_author(name = "bump_successful", url = submissions[0].shortlink)
                asyncio.gather(self.log("bot_commands", embed = embed))

                await asyncio.sleep(10)
                for submission in submissions:
                    submission.mod.sfw()

    @tasks.loop(minutes = 1)
    async def disboard_bump_available_notifier(self):
        if self.bump_available <= datetime.datetime.utcnow():
            bot_spam = self.get_channel("bot_spam")
            last_message = bot_spam.last_message
            bumper_role_mention = f"<@&{self._role_ids['bumper']}>"
            content = bumper_role_mention + ", a bump is available!"

            if last_message is None or last_message.content != content:
                await bot_spam.send(content)

    @tasks.loop(minutes = 30)
    async def temp_vc_poller(self):
        with database.connection_context():
            for temporary_voice_channel in TemporaryVoiceChannel:
                channel = temporary_voice_channel.channel
                if len(channel.members) == 0:
                    temporary_voice_channel.delete_instance()

    @tasks.loop(hours = 3)
    async def introduction_purger(self):
        tasks = []
        total_messages = 0
        messages_to_remove = []

        async for introduction in self.get_channel("introductions").history(limit=200):
            if isinstance(introduction.author, discord.User):
                messages_to_remove.append(introduction)
            total_messages += 1

        if len(messages_to_remove) >= (total_messages//2):
            return

        for introduction in messages_to_remove:
            embed = discord.Embed(
                color = self.bot.get_dominant_color(self.guild),
                title = f"Purged: Introduction by {introduction.author}",
                description = introduction.content
            )
            tasks.append(self.log("logs", embed = embed))
            tasks.append(introduction.delete())

        asyncio.gather(*tasks)


    @tasks.loop(seconds = 30)
    async def reminder_notifier(self):
        query = Reminder.select()
        query = query.where(Reminder.finished == False)
        query = query.where(Reminder.due_date <= datetime.datetime.utcnow())

        for reminder in query:
            channel = self.bot.get_channel(reminder.channel_id)
            asyncio.gather(channel.send(f"{reminder.user.mention}, Reminder: \n`{reminder.text}`"))
            reminder.finished = True
            reminder.save()

    @tasks.loop(hours = 1)
    async def illegal_member_notifier(self):
        for member in self.guild.members:
            if member.bot:
                continue

            if not member_is_legal(member):
                with database.connection_context():
                    time_here = relativedelta(datetime.datetime.utcnow(), member.joined_at)
                    if time_here.hours >= 6:
                        asyncio.gather(member.kick(reason = "Missing mandatory roles."))
                        await self.log("bot_commands", f"**{member}** {member.mention} was kicked due to missing roles")

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
                await self.log("bot_commands", f"**{human.user}** {human.mention} Should be celebrating their birthday today.")

def member_is_legal(member):
    age_roles = Intergalactica._role_ids["age"].values()
    gender_roles = Intergalactica._role_ids["gender"].values()

    has_age_role = False
    has_gender_role = False

    for role in member.roles:
        if role.id in age_roles:
            has_age_role = True
        elif role.id in gender_roles:
            has_gender_role = True

    return has_age_role and has_gender_role

def setup(bot):
    bot.add_cog(Intergalactica(bot))