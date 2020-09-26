import asyncio
import datetime

from emoji import emojize
import discord
from discord.ext import commands

# from src.models import Poll, Option, Settings, NamedEmbed, NamedChannel, database as db
from src.models import Poll, Option, Settings, NamedEmbed, database as db

class Intergalactica(commands.Cog):

    _role_ids = \
    {
        "selfies" : 748566253534445568,
        "nova"    : 748494888844132442
    }

    _channel_ids = \
    {
        "selfies"      : 744703465086779393,
        "concerns"     : 758296826549108746,
        "staff_chat"   : 750067502352171078,
        "bot_commands" : 754056523277271170
    }

    selfie_poll_question = "Should {member} get selfie perms?"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.guild_id = 742146159711092757



    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild

        welcome_channel = guild.system_channel

        text = "Welcome space cadet {member} {member.mention}!"


        # embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        # embed.set_author(name = f"Welcome space cadet {member}!", icon_url = guild.icon_url )
# 
        await welcome_channel.send(text.format(member = member))

        # with db:
        #     settings = Settings.get(guild_id = member.guild.id)
        #     embed = settings.embeds.where(NamedEmbed.name == "member_join").first()
        #     print(embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild

        welcome_channel = guild.system_channel

        text = "Goodbye space cadet {member} {member.mention}!"
        
        await welcome_channel.send(text.format(member = member))

        # embed = discord.Embed(color = self.bot.get_dominant_color(guild))
        # embed.set_author(name = f"Goodbye space cadet {member}!", icon_url = guild.icon_url )

        # await welcome_channel.send(embed = embed)
        # with db:
        #     settings = Settings.get(guild_id = member.guild.id)
        #     embed = settings.embeds.where(NamedEmbed.name == "member_leave").first()
        #     print(embed)


    def create_selfie_poll(self, member):
        guild = member.guild

        poll = Poll(
            question = self.selfie_poll_question.format(member = str(member)),
            author_id = self.bot.user.id,
            guild_id = guild.id,
            type = "bool"
        )

        options = []
        for i, reaction in enumerate((emojize(":white_heavy_check_mark:"), emojize(":prohibited:"))):
            option = Option(value = ("Yes","No")[i], reaction = reaction)
            options.append(option)

        poll.due_date = datetime.datetime.now() + datetime.timedelta(days = 2)

        selfie_channel = guild.get_channel(self._channel_ids["bot_commands"])
        result_channel = guild.get_channel(self._channel_ids["staff_chat"])

        poll.channel_id = selfie_channel.id
        poll.result_channel_id = result_channel.id

        with db:
            poll.save()

            for option in options:
                option.poll = poll
                option.save()
        
        return poll


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(after.roles) > len(before.roles):
            if after.guild.id != self.guild_id:
                return
            
            if self.bot.production:
                return
            return

            added_role = None
            has_selfie_perms = None

            for role in after.roles:
                if role not in before.roles:
                    added_role = role
                if role.id == self._role_ids["selfies"]:
                    has_selfie_perms = True
            
            if added_role.id == self._role_ids["nova"] and not has_selfie_perms:
                with db:
                    try:
                        poll = Poll.get(question = self.selfie_poll_question.format(member = str(after), ended = False))
                    except Poll.DoesNotExist:
                        
                        channel = guild.get_channel(self._channel_ids["bot_commands"])
                        await channel.send("Would send a selfie poll here")

                        # poll = self.create_selfie_poll(after)

                        # message = await poll.send()
                        # poll.message_id = message.id
                        # poll.save()

                        # await message.pin()



    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     if "clark" in message.content.lower():
    #         await message.channel.trigger_typing() 

    def member_is_legal(self, member):
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

    def illegal_member_iterator(self):
        for member in self.guild.members:
            if member.bot:
                continue

            if not self.member_is_legal(member):
                yield member

    @commands.command()
    async def mandatorycheck(self, ctx):
        embed = discord.Embed(color = ctx.guild_color, title = "Members without mandatory roles")

        lines = []
        for member in self.illegal_member_iterator():
            lines.append(f"{member.mention} joined: {member.joined_at.date().isoformat()}")

        embed.description = "\n".join(lines)

        await ctx.send(embed = embed)

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def purgeintros(self, ctx):
        channel = ctx.guild.get_channel(742567349613232249)

        coros = []
        async for message in channel.history(limit=200):
            if not isinstance(message.author, discord.Member):
                embed = discord.Embed(
                    color = ctx.guild_color,
                    title = f"Introduction by {message.author}",
                    description = message.content)
                coros.append( ctx.send(embed = embed) )

                await message.delete()

        if len(coros) == 0:
            embed = discord.Embed(title ="Nothing to purge.", color = ctx.guild_color)
            coros.append( ctx.send(embed = embed) )

        asyncio.gather(*coros)





def setup(bot):
    bot.add_cog(Intergalactica(bot))