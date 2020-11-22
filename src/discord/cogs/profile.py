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
import src.discord.helpers.pretty as pretty
import src.config as config
from src.utils.timezone import Timezone
from src.discord.errors.base import SendableException
from src.discord.helpers.paginating import Page, Paginator
import src.utils.general as general

def is_tester(member):
    with database.connection_context():
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
        cost = 10
        human, _ = Human.get_or_create(user_id = ctx.author.id)
        if human.gold < cost:
            raise SendableException(ctx.translate("not_enough_gold").format(cost = cost))

        asyncio.gather(ctx.message.delete())
        asyncio.gather(ctx.send(text))
        human.gold -= cost
        human.save()

    @commands.command()
    async def scoreboard(self, ctx):
        query = Human.select()
        query = query.join(Earthling, on=(Human.id == Earthling.human))
        query = query.where(Earthling.guild_id == ctx.guild.id)
        query = query.order_by(Human.gold.desc())

        embed = discord.Embed(title = "Scoreboard")

        table = pretty.Table()
        table.add_row(pretty.Row(["rank", "gold", "member"], header = True))

        top = 1
        i = (top-1)
        for human in query:
            values = [f"{i+1}", str(human.gold), str(human.user)]
            table.add_row(pretty.Row(values))
            if table.row_count == 11:
                break
            i += 1

        embed.description = table.generate()

        await ctx.send(embed = embed)

    @commands.group()
    async def profile(self, ctx, members : commands.Greedy[discord.Member]):
        if ctx.invoked_subcommand is not None:
            return

        member = members[0] if len(members) else ctx.author

        embed = discord.Embed(color = ctx.author.color)
        human, _ = Human.get_or_create(user_id = member.id)

        field = human.get_embed_field()
        embed.title = field["name"]
        values = field["value"]

        if human.country:
            embed.set_thumbnail(url = human.country.flag())

        footer = []
        unread_mail = human.inbox.where(Mail.read == False).where(Mail.finished == True)
        if len(unread_mail) > 0:
            footer.append(f"You have {unread_mail.count()} unread mail! use '{ctx.prefix}inbox' to view")

        # embed.timestamp = human.next_birthday
        # if embed.timestamp is not None:
        #     footer.append("Next birthday at")

        if len(footer) > 0:
            embed.set_footer(text = "\n".join(footer))

        embed.description = values

        await ctx.send(embed = embed)

    @profile.command(name = "compare")
    async def profile_compare(self, ctx, member : discord.Member):
        embed = discord.Embed(color = ctx.guild_color)

        humans = [Human.get_or_create(user_id = x.id)[0] for x in (ctx.author, member)]

        for human in humans:
            embed.add_field(**human.get_embed_field(show_all = True))

        await ctx.send(embed = embed)

    @profile.command(name = "clear", aliases = ["reset"])
    async def profile_clear(self, ctx):
        human, _ = Human.get_or_create(user_id = ctx.author.id)
        human.timezone      = None
        human.city          = None
        human.country       = None
        human.date_of_birth = None
        human.save()
        await ctx.send(ctx.translate("profile_cleared"))

    @profile.command(name = "setup")
    async def profile_setup(self, ctx, fields : commands.Greedy[str.lower]):
        human, _ = Human.get_or_create(user_id = ctx.author.id)

        if len(fields) == 0 or "city" in fields:
            waiter = CityWaiter(ctx, prompt =  ctx.translate("human_city_prompt"), skippable = True)
            try:
                city = await waiter.wait()
                human.city = city.name
            except Skipped:
                pass

        timezone_set = False
        if len(fields) == 0 or "country" in fields:
            await human.editor_for(ctx, "country")

        if human.city is not None and human.country is not None:
            city = self.bot.owm_api.by_q(human.city, human.country.alpha_2)
            if city is not None:
                human.timezone = str(city.timezone)
                timezone_set = True

        if not timezone_set or "country" in fields:
            await human.editor_for(ctx, "timezone")

        if len(fields) == 0 or "dateofbirth" in fields:
            await human.editor_for(ctx, "date_of_birth")

        human.save()
        await ctx.send(embed = Embed.success(ctx.translate("profile_setup")))

    @commands.command()
    async def events(self, ctx, month : int = None):
        if month is None:
            month = datetime.datetime.utcnow().month
        month = max(min(month, 12), 1)

        query = Human.select()
        query = query.where(Human.date_of_birth != None)
        query = query.where(Human.date_of_birth.month == month)
        query = query.order_by(Human.date_of_birth.asc())

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
            await item.editor_for(ctx, "name", skippable = not new)

        await item.editor_for(ctx, "description", skippable = not new)
        await item.editor_for(ctx, "rarity", skippable = True)
        await item.editor_for(ctx, "explorable", skippable = True)

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

        await item.editor_for(ctx, "rarity", skippable = True)
        await item.editor_for(ctx, "explorable", skippable = True)

        item.save()
        await ctx.send("OK")

    @commands.is_owner()
    @item.command(name = "give")
    async def item_give(self, ctx, member : discord.Member, *, name):
        if name == "":
            raise commands.errors.MissingRequiredArgument("name")
        try:
            item = Item.get(name = name)
        except Item.DoesNotExist:
            raise SendableException("Item not found.")

        member = member or ctx.author
        human, _ = Human.get_or_create(user_id = member.id)
        human.add_item(item, 1)
        await ctx.send("added")

    @item.command(name = "list")
    async def item_list(self, ctx):
        items = list(Item)
        items.sort(key = lambda x : x.rarity.value, reverse = True)

        table = pretty.Table()
        table.add_row(pretty.Row(("name", "rarity"), header = True))
        for item in items:
            table.add_row(pretty.Row((item.name, item.rarity.name)))
        paginator = table.to_paginator(ctx, 10)
        await paginator.wait()

    @commands.command()
    async def inventory(self, ctx):
        human, _ = Human.get_or_create(user_id = ctx.author.id)

        data = [(x.item.name, x.amount) for x in human.human_items if x.amount > 0]
        data.insert(0, ("name", "amount"))
        table = pretty.Table.from_list(data, first_header = True)
        await table.to_paginator(ctx, 10).wait()

    @item.command(name = "view")
    async def item_view(self, ctx,*, name):
        item = Item.get(name = name)
        await ctx.send(embed = item.embed)

    async def cog_before_invoke(self, ctx):
        attr_name = (ctx.command.root_parent or ctx.command).callback.__name__
        ctx.attr_name = attr_name

def setup(bot):
    bot.add_cog(Profile(bot))