import asyncio
import datetime
import random
import string

import discord
from discord.ext import commands, tasks
import emoji

from src.models import Human
from src.discord.helpers.converters import convert_to_date
import src.config as config
from src.utils.timezone import Timezone

emojize = lambda x : emoji.emojize(x, use_aliases=True)

db = Human._meta.database

class WeirdFont:
    __slots__ = ("char_mapping",)

    def __init__(self, alphabet):
        self.char_mapping = {}
        i = 0
        for letter in (string.ascii_lowercase + string.ascii_uppercase):
            self.char_mapping[letter] = alphabet[i]
            i += 1

    def __call__(self, text):
        return self.convert(text)

    def convert(self, text):
        new = []
        for letter in text:
            if letter in self.char_mapping:
                new.append(self.char_mapping[letter])
            else:
                new.append(letter)

        return "".join(new)
    
    @classmethod
    def italica(cls):
        return cls("𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘲𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘘𝘠𝘟")


font = WeirdFont.italica()


class Profile(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.command()
    async def parrot(self, ctx, *, text):
        await ctx.send(text)

    @commands.command()
    async def font(self, ctx, *, text):
        await ctx.send(font(text))


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if message.channel.name.lower() in ("votes", "suggestions"):
            await self.bot.vote_for(message)

        with db:
            human, _ = Human.get_or_create_for_member(message.author)

            if human.is_eligible_for_xp:
                human.experience += random.randint(config.min_xp, config.max_xp)
                human.last_experience_given = datetime.datetime.now()
                human.save()

                # rank_role = human.rank_role_should_have

                # if not rank_role:
                #     return

                # roles_to_remove = [x.role for x in RankRole.select().where(RankRole.guild_id == message.guild.id) if x.role in message.author.roles and x.role != rank_role.role]
                # await message.author.remove_roles(*roles_to_remove)

                # if rank_role.role not in message.author.roles:
                #     await message.author.add_roles(rank_role.role)
                #     await message.channel.send(self.bot.translate("new_rank_achieved").format(role = rank_role.role))


    @commands.command()
    async def profile(self, ctx, members : commands.Greedy[discord.Member]):
        if ctx.author not in members:
            members.insert(0, ctx.author)

        with db:
            embed = discord.Embed(color = ctx.author.color)
            for member in members:
                human, _ = Human.get_or_create_for_member(member)

                embed.add_field(**human.get_embed_field(show_all = len(members) > 1))

            await ctx.send(embed = embed)

    @commands.group(name="dateofbirth")
    async def date_of_birth(self, ctx):
        pass

    @date_of_birth.command(name="=", aliases=["add"], usage = (datetime.date.today() - datetime.timedelta(days=(365 * 20))) )
    async def assign_date_of_birth(self, ctx, date_of_birth : convert_to_date):
        """Adds a date of birth"""

        if date_of_birth >= datetime.date.today():
            return await ctx.send(ctx.bot.translate("date_cannot_be_in_future"))

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.date_of_birth = date_of_birth
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = str(date_of_birth)))

    @date_of_birth.command(name = "delete")
    async def delete_date_of_birth(self, ctx):
        with db:
            human, _ = Human.get_or_create_for_member(member)

            human.date_of_birth = None
            human.save()

        await ctx.send(ctx.bot.translate("attr_removed".format(name = ctx.attr_name)))


    @commands.group()
    async def timezone(self, ctx):
        pass

    @timezone.command(name="=", aliases=["add"], usage = lambda : "Europe/Amsterdam" )
    async def assign_timezone(self, ctx, timezone : Timezone):
        """Adds a timezone"""

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.timezone = timezone.name
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))

    @timezone.command(name = "city")
    async def timezone_city(self, ctx, city : str):
        """Adds a timezone"""
        timezone = Timezone.from_city(city)

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.timezone = timezone.name
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))

    @timezone.command(name = "hour")
    async def timezone_hour(self, ctx, hour : str):
        """Adds a timezone"""

        if "PM" in hour.upper():
            hour = int(hour.lower().replace("pm", "").strip()) + 12
        elif "AM" in hour.upper():
            hour = int(hour.lower().replace("am", "").strip())

        if hour == 24:
            hour = 0

        timezone = Timezone.from_hour(int(hour))

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.timezone = timezone.name
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))


    @timezone.command(name = "delete")
    async def delete_timezone(self, ctx):
        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.timezone = None
            human.save()

        await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))


    async def edit_personal_role(self, ctx, **kwargs):
        attr_name = ctx.command.name

        attr_value = kwargs[attr_name]

        if attr_name == "name":
            kwargs["color"] = ctx.guild_color
        elif attr_name == "color":
            kwargs["name"] = ctx.author.display_name

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)
            new = human.personal_role_id is None or human.personal_role is None

            if new:
                first_human = Human.select().where(Human.personal_role_id != None).limit(1).first()
                position = first_human.personal_role.position if first_human else 0

                role = await ctx.guild.create_role(**kwargs)
                await role.edit(position = position)
                human.personal_role = role
                human.save()
                await ctx.send(ctx.bot.translate("role_created").format(role = role))
                await ctx.author.add_roles(role)
            else:
                role = human.personal_role

                await role.edit(**{attr_name : attr_value})
                
                msg = ctx.bot.translate(f"attr_added").format(name = "role's " + attr_name, value = attr_value)
                embed = discord.Embed(color = role.color, title = msg)
                await ctx.send(embed = embed)

    @commands.group()
    async def role(self, ctx):

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)
            rank_role = human.rank_role

        allowed = rank_role is not None or ctx.author.is_nitro_booster()

        if allowed is None:
            await ctx.send("You are not allowed to run this command yet.")
            raise Exception()


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
                human, _ = Human.get_or_create_for_member(ctx.author)
                human.personal_role_id = role.id
                human.save()

            await ctx.send("All done.")

    @role.command()
    async def name(self, ctx, *, name : str):
        await self.edit_personal_role(ctx, name = name)

    @role.command(name = "delete")
    async def delete_role(self, ctx):
        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)
            if human.personal_role_id is not None:
                role = human.personal_role
                if role is not None:
                    await role.delete()

                human.personal_role_id = None
                human.save()

                await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    @commands.command()
    @commands.is_owner()
    async def resethumans(self, ctx):
        for human in Human:
            if human.personal_role_id is not None:
                role = human.personal_role
                if role is not None and human.member is None:
                    await role.delete()
                    print(f"Deleted {role}")



    @commands.group()
    async def city(self, ctx):
        pass

    @city.command(name="=", aliases=["add"], usage = "Munstergeleen" )
    async def assign_city(self, ctx, city : str):
        """Adds a city"""

        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.city = city
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = city))

    @city.command(name = "delete")
    async def delete_city(self, ctx):
        with db:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.city = None
            human.save()

        await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))


    @commands.command()
    async def addrankrole(self, ctx, role : discord.Role, required_experience : int):
        RankRole.create(role_id = role.id, required_experience = required_experience, guild_id = ctx.guild.id)
        await ctx.send("rank_role_added")

    @commands.has_guild_permissions(manage_roles = True)
    @commands.group()
    async def xp(self, ctx):
        pass

    @xp.command(name="+")
    async def addxp(self, ctx, member : discord.Member, xp : int):
        """Adds an amount of xp from a member."""

        with db:
            human, _ = Human.get_or_create_for_member(member)

            human.experience += xp
            human.save()

        await ctx.send(ctx.bot.translate("xp_added"))

    @xp.command(name="-")
    async def removexp(self, ctx, member : discord.Member, xp : int):
        """Adds an amount of xp from a member."""

        with db:
            human, _ = Human.get_or_create_for_member(member)

            human.experience -= xp
            human.save()

        await ctx.send(ctx.bot.translate("xp_removed"))


    async def cog_before_invoke(self, ctx):
        attr_name = (ctx.command.root_parent or ctx.command).callback.__name__
        ctx.attr_name = ctx.bot.translate(attr_name)





def setup(bot):
    bot.add_cog(Profile(bot))