import asyncio
import datetime
import random
import string

import discord
from discord.ext import commands, tasks
import emoji

from src.models import Human, GlobalHuman, database
from src.discord.helpers.converters import convert_to_date
from src.discord.helpers.waiters import *
import src.config as config
from src.utils.timezone import Timezone
from src.discord.errors.base import SendableException

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
    def from_full_alphabet(cls, text):
        pass

    @classmethod
    def regional(cls):
        return cls("🇦🇧🇨🇩🇪🇫🇬🇭🇯🇮🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿")

    @classmethod
    def italica(cls):
        return cls("𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘲𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘘𝘠𝘟")

font = WeirdFont.italica()

class CityWaiter(StrWaiter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, max_words = None, **kwargs)

    def convert(self, argument):
        if argument.isdigit():
            city = self.bot.owm_api.by_id(argument)
        else:
            city = self.bot.owm_api.by_q(*argument.split(","))

        if city is None:
            raise ConversionFailed("City was not found.")

        return city

class Profile(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.command()
    async def parrot(self, ctx, *, text):
        await ctx.send(text)

    @commands.command()
    @commands.is_owner()
    async def font(self, ctx, *, text):
        await ctx.send(font(text))

    @commands.command(name = "givegold")
    async def give_gold(self, ctx, member : discord.Member, amount : int):
        if member.id == ctx.author.id:
            raise SendableException(ctx.translate("cannot_send_gold_to_self"))

        with database:
            sender, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)
            if sender.gold < amount:
                raise SendableException(ctx.translate("not_enough_gold"))
            sendee, _ = GlobalHuman.get_or_create(user_id = member.id)

            sender.gold -= amount
            sendee.gold += amount
            sendee.save()
            sender.save()

            asyncio.gather(ctx.send(ctx.translate("gold_sent")))

    @commands.command()
    async def scoreboard(self, ctx):
        query = Human.select().where(Human.guild_id == ctx.guild.id)
        query = query.join(GlobalHuman, on=(Human.global_human == GlobalHuman.id))
        query = query.order_by(GlobalHuman.gold.desc())
        query = query.limit(10)

        embed = discord.Embed(title = "Scoreboard")

        with database:
            humans = list(query)

        rows = []
        i = 0
        for human in humans:
            values = []
            values.append(f"{i+1}")
            values.append(str(human.global_human.gold))
            values.append(str(human.member))
            rows.append(values)
            i += 1

        headers = ["rank", "gold", "member"]
        sep = " | "
        lines = []
        longests = [len(x) for x in headers]
        padding = 2
        for row in rows:
            row_text = []
            for i in range(len(row)):
                value = row[i]
                if len(value) > longests[i]:
                    longests[i] = len(value)

                row_text.append(value.ljust(longests[i]+padding) )
            lines.append(sep.join(row_text))

        lines.insert(0, sep.join([x.ljust(longests[i]+padding) for i,x in enumerate(headers)]) )

        equals = sum(longests) + (len(headers) * (padding) ) + len(sep) + padding
        lines.insert(1, "=" * equals )

        embed.description = "```md\n" + ( "\n".join(lines) ) + "```"

        await ctx.send(embed = embed)

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     if message.author.bot or not message.guild:
    #         return

    #     if message.channel.name.lower() in ("votes", "suggestions"):
    #         await self.bot.vote_for(message)

    #     with database:
    #         human, _ = Human.get_or_create_for_member(message.author)

    #         if human.is_eligible_for_xp:
    #             human.experience += random.randint(config.min_xp, config.max_xp)
    #             human.last_experience_given = datetime.datetime.utcnow()
    #             human.save()

    @commands.group()
    async def profile(self, ctx, members : commands.Greedy[discord.Member]):
        if ctx.invoked_subcommand is None:
            if ctx.author not in members:
                members.insert(0, ctx.author)

            with database:
                embed = discord.Embed(color = ctx.author.color)
                for member in members:
                    human, _ = Human.get_or_create_for_member(member)
                    embed.add_field(**human.get_embed_field(show_all = len(members) > 1))

                await ctx.send(embed = embed)

    @profile.command(name = "clear", aliases = ["reset"])
    async def profile_clear(self, ctx):
        with database:
            human, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)
            human.timezone      = None
            human.city          = None
            human.country_code  = None
            human.date_of_birth = None
            human.save()
            await ctx.send(ctx.translate("profile_cleared"))

    @profile.command(name = "setup")
    async def profile_setup(self, ctx):
        prompt = lambda x : ctx.translate(f"profile_{x}_prompt")

        with database:
            human, _ = GlobalHuman.get_or_create(user_id = ctx.author.id)

            waiter = CityWaiter(ctx, prompt = prompt("city"), skippable = True)
            try:
                city = await waiter.wait()
            except Skipped:
                pass
            else:
                human.city = city.name

            timezone_set = False
            waiter = CountryWaiter(ctx, prompt = prompt("country"), skippable = True)
            try:
                country = await waiter.wait()
            except Skipped:
                pass
            else:
                human.country_code = country.alpha_2
                if human.city is not None:
                    city = self.bot.owm_api.by_q(human.city, human.country_code)
                    human.timezone = str(city.timezone)
                    timezone_set = True

            if not timezone_set:
                waiter = TimezoneWaiter(ctx, prompt = prompt("timezone"), skippable = True)
                try:
                    human.timezone = await waiter.wait()
                except Skipped:
                    pass

            waiter = DateWaiter(ctx, prompt = prompt("date_of_birth"), skippable = True)
            try:
                human.date_of_birth = await waiter.wait()
            except Skipped:
                pass

            human.save()
            await ctx.send(ctx.translate("profile_setup"))

    @commands.group(name="dateofbirth")
    async def date_of_birth(self, ctx):
        pass

    @date_of_birth.command(name="=", aliases=["add"], usage = (datetime.date.today() - datetime.timedelta(days=(365 * 20))) )
    async def assign_date_of_birth(self, ctx, date_of_birth : convert_to_date):
        """Adds a date of birth"""
        if date_of_birth >= datetime.date.today():
            return await ctx.send(ctx.bot.translate("date_cannot_be_in_future"))

        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)
            human.global_human.date_of_birth = date_of_birth
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = str(date_of_birth)))

    @date_of_birth.command(name = "delete")
    async def delete_date_of_birth(self, ctx):
        with database:
            human, _ = Human.get_or_create_for_member(member)
            human.global_human.date_of_birth = None
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_removed".format(name = ctx.attr_name)))


    @commands.group()
    async def timezone(self, ctx):
        pass

    @timezone.command(name="=", aliases=["add"], usage = lambda : "Europe/Amsterdam" )
    async def assign_timezone(self, ctx, timezone : Timezone):
        """Adds a timezone"""

        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)
            human.global_human.timezone = timezone.name
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))

    @timezone.command(name = "city")
    async def timezone_city(self, ctx, city : str):
        """Adds a timezone"""
        timezone = Timezone.from_city(city)

        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)
            human.global_human.timezone = timezone.name
            human.global_human.save()

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

        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.global_human.timezone = timezone.name
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))


    @timezone.command(name = "delete")
    async def delete_timezone(self, ctx):
        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.global_human.global_human.timezone = None
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    async def edit_personal_role(self, ctx, **kwargs):
        attr_name = ctx.command.name
        attr_value = kwargs[attr_name]

        if attr_name == "name":
            kwargs["color"] = ctx.guild_color
        elif attr_name == "color":
            kwargs["name"] = ctx.author.display_name

        with database:
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
        if ctx.guild.id == 742146159711092757:
            with database:
                human, _ = Human.get_or_create_for_member(ctx.author)
                rank_role = human.rank_role

            allowed = rank_role is not None or ctx.author.premium_since is not None

            if not allowed:
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
        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)
            if human.personal_role_id is not None:
                role = human.personal_role
                if role is not None:
                    await role.delete()

                human.personal_role_id = None
                human.save()

                await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    @role.command(name = "reset")
    @commands.is_owner()
    async def reset_roles(self, ctx):
        for human in Human:
            if human.personal_role_id is not None:
                role = human.personal_role
                if role is not None and human.member is None:
                    await role.delete()

    @commands.group()
    async def city(self, ctx):
        pass

    @city.command(name="=", aliases=["add"], usage = "Munstergeleen" )
    async def assign_city(self, ctx, city : str):
        """Adds a city"""

        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.global_human.city = city
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = city))

    @city.command(name = "delete")
    async def delete_city(self, ctx):
        with database:
            human, _ = Human.get_or_create_for_member(ctx.author)

            human.global_human.city = None
            human.global_human.save()

        await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    async def cog_before_invoke(self, ctx):
        attr_name = (ctx.command.root_parent or ctx.command).callback.__name__
        # ctx.attr_name = ctx.bot.translate(attr_name)
        ctx.attr_name = attr_name





def setup(bot):
    bot.add_cog(Profile(bot))