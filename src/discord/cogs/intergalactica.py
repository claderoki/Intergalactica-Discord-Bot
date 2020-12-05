import asyncio
import datetime
import typing

from emoji import emojize
import discord
from discord.ext import commands, tasks

from src.discord.errors.base import SendableException
from src.models import Poll, PollTemplate, Option, Settings, Item, NamedEmbed, Human, Earthling, TemporaryChannel, HumanItem, database
from src.discord.helpers.waiters import IntWaiter

def is_intergalactica():
    def predicate(ctx):
        return ctx.guild and ctx.guild.id == Intergalactica.guild_id
    return commands.check(predicate)

class Intergalactica(commands.Cog):
    guild_id = 742146159711092757

    _role_ids = {
        "selfies" : 748566253534445568,
        "5k+"     : 778744417322139689,
        "bumper"  : 780001849335742476,
        "age"     : {"18-20": 748606669902053387, "21-24": 748606823229030500, "25-29": 748606893387153448, "30+": 748606902363095206},
        "gender"  : {"male": 742301620062388226, "female": 742301646004027472, "other" : 742301672918745141},
        "ranks"   : {
            "luna"      : 748494880229163021,
            "nova"      : 748494888844132442,
            "aurora"    : 748494890127851521,
            "aquila"    : 748494890169794621,
            "orion"     : 748494891419697152,
            "andromeda" : 748494891751047183
        }
    }

    _channel_ids = {
        "selfies"       : 744703465086779393,
        "concerns"      : 758296826549108746,
        "staff_chat"    : 750067502352171078,
        "bot_spam"      : 742163352712642600,
        "bot_commands"  : 754056523277271170,
        "introductions" : 742567349613232249,
        "tabs"          : 757961433911787592,
        "logs"          : 745010147083944099
    }

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

        if self.bot.production:
            self.temp_channel_checker.start()
            self.disboard_bump_available_notifier.start()
            self.introduction_purger.start()
            await asyncio.sleep( (60 * 60) * 3 )
            self.birthday_poller.start()
            self.illegal_member_notifier.start()

    def on_milkyway_purchased(self, channel, member, amount):
        with database.connection_context():
            item = Item.get(name = "Milky way")
            human, _ = Human.get_or_create(user_id = member.id)
            human.add_item(item, amount)

        embed = discord.Embed(color = self.bot.get_dominant_color(None))
        embed.description = f"Good job in purchasing {amount} milky way(s).\nInstructions:\n`/milkyway create` or `/milkyway extend #channel`"
        asyncio.gather(channel.send(embed = embed))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.production:
            return
        if message.guild and message.guild.id != self.guild_id:
            return

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

        if message.content == "!d bump":
            disboard_response = await self.bot.wait_for("message", check = lambda x : x.author.id == 302050872383242240 and x.channel.id == message.channel.id)
            embed = disboard_response.embeds[0]
            text = embed.description

            if "minutes until the server can be bumped" in text:
                minutes = int([x for x in text.split() if x.isdigit()][0])
            elif "👍" in text or "Bump done" in text:
                minutes = 120
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

        await welcome_channel.send(embed = embed)

    async def create_selfie_poll(self, ctx, member):
        poll = Poll.from_template(PollTemplate.get(name = "selfies"))
        poll.question = f"Should {member} be given selfie access?"
        poll.author_id = ctx.author.id
        poll.save()
        poll.create_options(("Yes", "No", "Idk them well enough yet"))
        await poll.send()
        poll.save()
        return poll

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def selfiepoll(self, ctx, member : discord.Member):
        await self.create_selfie_poll(ctx, member)
        await ctx.success()

    def get_milkyway_human_item(self, user):
        human_item = HumanItem.get_or_none(
            human = Human.get_or_create(user_id = user.id)[0],
            item = 33
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
        asyncio.gather(self.log("bot_commands", f"**{member}** {member.mention} has achieved {role.name}!"))
        role = self.guild.get_role(self._role_ids["5k+"])
        asyncio.gather(member.add_roles(role))

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
            await ctx.author.add_roles(role)
        else:
            role = earthling.personal_role
            await role.edit(**{attr_name : attr_value})
            msg = ctx.bot.translate(f"attr_added").format(name = "role's " + attr_name, value = attr_value)
            embed = discord.Embed(color = role.color, title = msg)
            await ctx.send(embed = embed)

    @commands.group()
    @is_intergalactica()
    async def role(self, ctx):
        earthling, _ = Earthling.get_or_create_for_member(ctx.author)
        rank_role = earthling.rank_role

        allowed = rank_role is not None or ctx.author.premium_since is not None

        if not allowed:
            raise SendableException("You are not allowed to run this command yet.")

    @role.command(name = "color", aliases = ["colour"])
    async def role_color(self, ctx, color : discord.Color = None):
        if ctx.author.id == 355186573119324161:
            return

        if color is None:
            color = self.bot.get_random_color()

        await self.edit_personal_role(ctx, color = color)

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

    @role.command(name = "name")
    async def role_name(self, ctx, *, name : str):
        await self.edit_personal_role(ctx, name = name)

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
        embed.title = "The following roles were purged:"
        lines = "`\n`".join(roles_deleted)
        embed.description = f"`{lines}`"
        asyncio.gather(ctx.send(embed = embed))

    @commands.command(aliases = [ x.name for x in NamedEmbed.select(NamedEmbed.name).where(NamedEmbed.settings == 2) ])
    async def getembed(self, ctx, numbers : commands.Greedy[int] = None):
        embed = self.embed_from_name(ctx.invoked_with, numbers)
        await ctx.send(embed = embed)

    def illegal_member_iterator(self):
        for member in self.guild.members:
            if member.bot:
                continue

            if not member_is_legal(member):
                yield member

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

    @tasks.loop(minutes = 1)
    async def disboard_bump_available_notifier(self):
        if self.bump_available <= datetime.datetime.utcnow():
            bot_spam = self.get_channel("bot_spam")
            last_message = bot_spam.last_message
            bumper_role_mention = f"<@&{self._role_ids['bumper']}>"
            content = bumper_role_mention + ", a bump is available!"

            if last_message is None or last_message.content != content:
                await bot_spam.send(content)

    @tasks.loop(hours = 12)
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

    @tasks.loop(hours = 24)
    async def illegal_member_notifier(self):
        for member in self.illegal_member_iterator():
            days = (datetime.datetime.utcnow() - member.joined_at).days
            if days > 1:
                await self.log("bot_commands", f"**{member}** {member.mention} is missing one or more of the mandatory roles.")

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
    age_roles       = [748606669902053387,748606823229030500,748606893387153448,748606902363095206]
    gender_roles    = [742301620062388226, 742301646004027472, 742301672918745141]

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