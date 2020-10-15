import asyncio
import datetime

from emoji import emojize
import discord
from discord.ext import commands, tasks

# from src.models import Poll, Option, Settings, NamedEmbed, NamedChannel, database as db
from src.models import Poll, Option, Settings, NamedEmbed, Human, database


class Intergalactica(commands.Cog):

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
        self.guild_id = 742146159711092757

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)
        self.bot.get_dominant_color(self.guild)
        if not self.bot.production:
            self.poller.start()


    async def log(self, channel_name, content = None, **kwargs):
        channel = self.get_channel(channel_name)
        await channel.send(content = content, **kwargs)

    async def on_member_leave_or_join(self, member, type):
        if not self.bot.production:
            return
        welcome_channel = member.guild.system_channel
        text = self.bot.translate("member_" + type)
        await welcome_channel.send(text.format(member = member))

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
                # return

                # with database:
                #     try:
                #         poll = Poll.get(question = self.selfie_poll_question.format(member = str(after), ended = False))
                #     except Poll.DoesNotExist:
                #         pass

                #         channel = guild.get_channel(self._channel_ids["bot_commands"])
                #         await channel.send("Would send a selfie poll here")

                        # poll = self.create_selfie_poll(after)

                        # message = await poll.send()
                        # poll.message_id = message.id
                        # poll.save()

                        # await message.pin()


    def embed_from_name(self, name, indexes):
        with database:
            named_embed = NamedEmbed.get(name = name)
        if indexes is not None:
            embed = named_embed.get_embed_only_selected_fields([x-1 for x in indexes])
        else:
            embed = named_embed.embed
        return embed

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
    async def poller(self):
        async for introduction in self.introductions_to_purge():
            embed = discord.Embed(
                color = self.bot.get_dominant_color(self.guild),
                title = f"Purged: Introduction by {introduction.author}",
                description = introduction.content)
            await self.log("logs", embed = embed)
            await introduction.delete()

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

        with database:
            for human in Human.select().where( (Human.guild_id == self.guild_id) & (Human.date_of_birth != None) ):
                if human.birthday:
                    await self.log("bot_commands", f"**{human.member}** {human.member.mention} Should be celebrating their birthday today.")




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