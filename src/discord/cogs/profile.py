import asyncio
import datetime
import random
import string

import discord
from discord.ext import commands, tasks
import emoji

from src.models import Human, Earthling, Mail, Item, database
from src.discord.helpers.converters import convert_to_date
from src.discord.helpers.waiters import *
from src.discord.helpers.pretty import prettify_dict
import src.config as config
from src.utils.timezone import Timezone
from src.discord.errors.base import SendableException

def is_tester(member):
    with database:
        human, _ = Human.get_or_create(user_id = member.id)
        return human.tester

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
        if ctx.author.id == self.bot.owner.id:
            asyncio.gather(ctx.message.delete())

        asyncio.gather(ctx.send(text))

    @commands.command()
    async def scoreboard(self, ctx):
        query = Earthling.select().where(Earthling.guild_id == ctx.guild.id)
        query = query.join(Human, on=(Earthling.human == Human.id))
        query = query.order_by(Human.gold.desc())

        embed = discord.Embed(title = "Scoreboard")

        top = 1
        rows = []
        i = (top-1)
        with database:
            for earthling in query:
                values = []
                member = earthling.member
                if member:
                    values.append(f"{i+1}")
                    values.append(str(earthling.human.gold))
                    values.append(str(member))
                    rows.append(values)
                    if len(rows) == 10:
                        break
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

    @commands.group()
    async def profile(self, ctx, members : commands.Greedy[discord.Member]):
        if ctx.invoked_subcommand is None:
            if ctx.author not in members:
                members.insert(0, ctx.author)

            with database:
                embed = discord.Embed(color = ctx.author.color)
                for member in members:
                    human, _ = Human.get_or_create(user_id = member.id)
                    field = human.get_embed_field(show_all = len(members) > 1)
                    unread_mail = human.inbox.where(Mail.read == False)
                    if len(unread_mail) > 0:
                        field["name"] += f"  | {len(unread_mail)} 📥"
                    embed.add_field(**field)

                await ctx.send(embed = embed)

    @profile.command(name = "clear", aliases = ["reset"])
    async def profile_clear(self, ctx):
        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
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
            human, _ = Human.get_or_create(user_id = ctx.author.id)

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
                    if city is not None:
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

    @commands.command()
    async def events(self, ctx, month : int = None):
        if month is None:
            month = datetime.datetime.utcnow().month
        month = max(min(month, 12), 1)

        query = Human.select()
        query = query.where(Human.date_of_birth != None)
        query = query.where(Human.date_of_birth.month == month)
        query = query.order_by(Human.date_of_birth.asc())

        with database:
            humans = [x for x in query if ctx.guild.get_member(x.user_id) is not None]

        lines = []
        for human in humans:
            lines.append(f"{human.user} - {human.date_of_birth}")
        if len(lines) > 0:
            embed = discord.Embed(color = ctx.guild_color)
            embed.set_author(name = "Birthdays", icon_url = ctx.guild.icon_url)
            embed.description = "\n".join(lines)
            await ctx.send(embed = embed)
        else:
            await ctx.send("No events this month")

    @commands.group()
    async def item(self, ctx):
        pass

    @item.command(name = "create", aliases = ["edit"])
    async def item_create(self, ctx,*, name):
        if name == "":
            raise commands.errors.MissingRequiredArgument("name")
        if not is_tester(ctx.author):
            raise SendableException(ctx.translate("not_a_tester"))

        item, new = Item.get_or_create(name = name)

        if not new:
            await item.editor_for("name", ctx, skippable = not new)

        await item.editor_for("description", ctx, skippable = not new)
        await item.editor_for("rarity", ctx, skippable = True)
        await item.editor_for("explorable", ctx, skippable = True)

        waiter = AttachmentWaiter(ctx, prompt = ctx.translate("item_image_prompt"), skippable = not new)
        try:
            item.image_url = await waiter.wait(store = True)
        except Skipped: pass

        item.save()
        await ctx.send("OK")

    @item.command(name = "explorable", aliases = ["exp"])
    async def item_explorable(self, ctx,*, name):
        if name == "":
            raise commands.errors.MissingRequiredArgument("name")

        if not is_tester(ctx.author):
            raise SendableException(ctx.translate("not_a_tester"))
        try:
            item = Item.get(name = name)
        except Item.DoesNotExist:
            raise SendableException("Item not found.")

        await item.editor_for("rarity", ctx, skippable = True)
        await item.editor_for("explorable", ctx, skippable = True)

        item.save()
        await ctx.send("OK")



    @item.command(name = "list")
    async def item_list(self, ctx):
        with database:
            lines = []
            for item in Item:
                if item.explorable:
                    line = f"{item.name} ({item.rarity.weight})"
                else:
                    line = item.name
                lines.append(line)

            embed = discord.Embed()
            lines = "\n".join(lines)
            embed.description = f"```\n{lines}```"
            embed.set_footer(text = f"To view more information about a specific item type '{ctx.prefix}item view <name>'")
            asyncio.gather(ctx.send(embed = embed))

    @commands.command()
    async def inventory(self, ctx):
        human, _ = Human.get_or_create(user_id = ctx.author.id)

        data = {}
        for human_item in human.human_items:
            data[human_item.item.name] = human_item.amount

        embed = discord.Embed(color = ctx.guild_color, description = f"```\n{prettify_dict(data)}```")
        asyncio.gather(ctx.send(embed = embed))

    @item.command(name = "view")
    async def item_view(self, ctx,*, name):
        with database:
            item = Item.get(name = name)
            await ctx.send(embed = item.embed)

    @commands.group(name="dateofbirth")
    async def date_of_birth(self, ctx):
        pass

    @date_of_birth.command(name="=", aliases=["add"], usage = (datetime.date.today() - datetime.timedelta(days=(365 * 20))) )
    async def assign_date_of_birth(self, ctx, date_of_birth : convert_to_date):
        """Adds a date of birth"""
        if date_of_birth >= datetime.date.today():
            return await ctx.send(ctx.bot.translate("date_cannot_be_in_future"))

        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
            human.date_of_birth = date_of_birth
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = str(date_of_birth)))

    @date_of_birth.command(name = "delete")
    async def delete_date_of_birth(self, ctx):
        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
            human.date_of_birth = None
            human.save()

        await ctx.send(ctx.bot.translate("attr_removed".format(name = ctx.attr_name)))

    @commands.group()
    async def timezone(self, ctx):
        pass

    @timezone.command(name="=", aliases=["add"], usage = lambda : "Europe/Amsterdam" )
    async def assign_timezone(self, ctx, timezone : Timezone):
        """Adds a timezone"""

        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
            human.timezone = timezone.name
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))

    @timezone.command(name = "city")
    async def timezone_city(self, ctx, city : str):
        """Adds a timezone"""
        timezone = Timezone.from_city(city)

        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)
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

        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)

            human.timezone = timezone.name
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = timezone.name))

    @timezone.command(name = "delete")
    async def delete_timezone(self, ctx):
        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)

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

        with database:
            human, _ = Earthling.get_or_create_for_member(ctx.author)
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
                human, _ = Earthling.get_or_create_for_member(ctx.author)
                rank_role = human.rank_role

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
        with database:
            earthling, _ = Earthling.get_or_create_for_member(ctx.author)
            if earthling.personal_role_id is not None:
                role = earthling.personal_role
                if role is not None:
                    await role.delete()

                earthling.personal_role_id = None
                earthling.save()

                await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    @role.command(name = "reset")
    @commands.is_owner()
    async def reset_roles(self, ctx):
        for earthling in Earthling:
            if earthling.personal_role_id is not None:
                role = earthling.personal_role
                if role is not None and earthling.member is None:
                    await role.delete()

    @commands.group()
    async def city(self, ctx):
        pass

    @city.command(name="=", aliases=["add"], usage = "Munstergeleen" )
    async def assign_city(self, ctx, city : str):
        """Adds a city"""

        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)

            human.city = city
            human.save()

        await ctx.send(ctx.bot.translate("attr_added").format(name = ctx.attr_name, value = city))

    @city.command(name = "delete")
    async def delete_city(self, ctx):
        with database:
            human, _ = Human.get_or_create(user_id = ctx.author.id)

            human.city = None
            human.save()

        await ctx.send(ctx.bot.translate("attr_removed").format(name = ctx.attr_name))

    async def cog_before_invoke(self, ctx):
        attr_name = (ctx.command.root_parent or ctx.command).callback.__name__
        ctx.attr_name = attr_name





def setup(bot):
    bot.add_cog(Profile(bot))