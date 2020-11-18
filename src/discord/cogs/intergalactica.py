import asyncio
import datetime

from emoji import emojize
import discord
from discord.ext import commands, tasks

from src.models import Poll, PollTemplate, Option, Settings, NamedEmbed, Earthling, database

def is_intergalactica():
    def predicate(ctx):
        return ctx.guild.id == Intergalactica.guild_id
    return commands.check(predicate)

class Intergalactica(commands.Cog):
    guild_id = 742146159711092757

    _role_ids = \
    {
        "selfies" : 748566253534445568,
        "nova"    : 748494888844132442,
        "luna"    : 748494880229163021,
        "age"     : {},
        "gender"  : {}
    }

    _channel_ids = \
    {
        "selfies"       : 744703465086779393,
        "concerns"      : 758296826549108746,
        "staff_chat"    : 750067502352171078,
        "bot_commands"  : 754056523277271170,
        "introductions" : 742567349613232249,
        "tabs"          : 757961433911787592,
        "logs"          : 745010147083944099
    }

    selfie_poll_question = "Should {member} get selfie perms?"

    def get_channel(self, name):
        return self.bot.get_channel(self._channel_ids[name])

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)
        self.bot.get_dominant_color(self.guild)

        if self.bot.production:
            await asyncio.sleep( (60 * 60) * 3 )
        #     self.introduction_purger.start()
            self.illegal_member_notifier.start()
            self.birthday_poller.start()


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

    async def create_selfie_poll(self, member):
        with database.connection_context():
            poll = Poll.from_template(PollTemplate.get(name = "selfies"))
            poll.question = f"Should {member} be given selfie access?"
            poll.save()
            poll.create_options(("Yes", "No", "I don't know them well enough yet"))
            await poll.send()
            poll.save()
            return poll

    @commands.has_guild_permissions(administrator = True)
    @commands.command()
    async def selfiepoll(self, ctx, member : discord.Member):
        await self.create_selfie_poll(member)
        await ctx.success()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.on_member_leave_or_join(member, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.on_member_leave_or_join(member, "leave")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(after.roles) > len(before.roles):
            if after.guild.id != self.guild_id:
                return

            if not self.bot.production:
                return

            added_role = None
            has_selfie_perms = None

            for role in after.roles:
                if role not in before.roles:
                    added_role = role
                if role.id == self._role_ids["selfies"]:
                    has_selfie_perms = True

            if added_role.id == self._role_ids["luna"] and not has_selfie_perms:
                await self.log("bot_commands", f"**{after}** {after.mention} has achieved Luna!")

    def embed_from_name(self, name, indexes):
        with database.connection_context():
            named_embed = NamedEmbed.get(name = name)
        if indexes is not None:
            embed = named_embed.get_embed_only_selected_fields([x-1 for x in indexes])
        else:
            embed = named_embed.embed
        return embed

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
            first_earthling = Earthling.select().where(Earthling.personal_role_id != None).limit(1).first()
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

    @role.command(aliases = ["colour"])
    async def color(self, ctx, color : discord.Color = None):
        if color is None:
            color = self.bot.get_random_color()

        await self.edit_personal_role(ctx, color = color)

    @commands.is_owner()
    @role.command()
    async def link(self, ctx, role : discord.Role):
        members = role.members

        if len(members) > 3:
            await ctx.send("Too many people have this role.")
        else:
            for member in role.members:
                human, _ = Earthling.get_or_create_for_member(ctx.author)
                human.personal_role_id = role.id
                human.save()

            await ctx.send(ctx.translate("roles_linked"))

    @role.command()
    async def name(self, ctx, *, name : str):
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
    async def reset_roles(self, ctx):
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

    async def introductions_to_purge(self):
        async for message in self.get_channel("introductions").history(limit=200):
            if isinstance(message.author, discord.User):
                yield message

    def illegal_member_iterator(self):
        for member in self.guild.members:
            if member.bot:
                continue

            if not member_is_legal(member):
                yield member

    @tasks.loop(hours = 12)
    async def introduction_purger(self):
        return
        tasks = []
        async for introduction in self.introductions_to_purge():
            embed = discord.Embed(
                color = self.bot.get_dominant_color(self.guild),
                title = f"Purged: Introduction by {introduction.author}",
                description = introduction.content)
            tasks.append(self.log("logs", embed = embed))
            tasks.append(introduction.delete())

        if len(tasks) > 3*2:
            pass
        else:
            asyncio.gather(*tasks)

    @tasks.loop(hours = 24)
    async def illegal_member_notifier(self):
        for member in self.illegal_member_iterator():
            days = (datetime.datetime.utcnow() - member.joined_at).days
            if days > 1:
                await self.log("bot_commands", f"**{member}** {member.mention} is missing one or more of the mandatory roles.")
                continue
                # try:
                #     await member.send(content = f"Hello. In the **{self.guild.name}**  server, both the gender role and the age role are mandatory. Please pick these roles up.")
                # except discord.Forbidden:
                # else:
                #     await self.log("tabs", f"DMed **{member}** {member.mention} to ask them to pick up mandatory roles.")
                # embed = self.embed_from_name("rules", [7])

    @tasks.loop(hours = 12)
    async def birthday_poller(self):
        with database.connection_context():
            for earthling in Earthling.select().where( Earthling.guild_id == self.guild_id ):
                human = earthling.human
                if human.birthday:
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