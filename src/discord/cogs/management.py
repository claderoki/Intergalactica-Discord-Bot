import re

import discord
from discord.ext import commands

import src.config as config
from src.models import Rule, Settings, EmojiUsage, database as db

emoji_match = lambda x : [int(x) for x in re.findall(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>', x)]

def increment_emoji(guild, emoji):
    with db:
        usage, _ = EmojiUsage.get_or_create(guild_id = guild.id, emoji_id = emoji.id)
        usage.total_uses += 1
        usage.save()

class Management(discord.ext.commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not config.production:
            return

        if message.author.bot:
            return

        ids = emoji_match(message.content)
        for id in ids:
            emoji = self.bot.get_emoji(id)
            if emoji in message.guild.emojis:
                increment_emoji(message.guild, emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not config.production:
            return

        emoji = payload.emoji

        if payload.member.bot:
            return

        if emoji.id is None:
            return

        member = payload.member

        if emoji not in member.guild.emojis:
            return

        increment_emoji(member.guild, emoji)

    @commands.command()
    async def leastemoji(self, ctx):
        emoji_usages = list(EmojiUsage.select().where(EmojiUsage.guild_id == ctx.guild.id).order_by(EmojiUsage.total_uses.desc()) )
        emoji_ids = [x.emoji_id for x in emoji_usages]

        with db:
            for emoji in ctx.guild.emojis:
                if emoji.id is not None:
                    if emoji.id not in emoji_ids:
                        emoji_usages.append( EmojiUsage.create(guild_id = ctx.guild.id, emoji_id = emoji.id) )

            embed = discord.Embed(color = discord.Color.purple())
            embed.description = ""

            for usage in emoji_usages[-10:-1]:
                embed.description += f"{usage.emoji} = {usage.total_uses}\n"

            await ctx.send(embed = embed)



    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def resetchannel(self, ctx, channel : discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        await channel.clone()
        await channel.delete()


    @commands.command()
    async def guidelines(self, ctx):
        if ctx.guild is None:
            guild = ctx.bot.get_guild(742146159711092757)
        else:
            guild = ctx.guild


        embed = discord.Embed(color = discord.Color.purple())
        embed.set_author(name = guild.name + " Guidelines", icon_url = guild.icon_url)
        # embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/705361372179070987/750809414977454180/Guidelines.png")

        guidelines = \
        [
            "Please stay active! Notify mods if you intend to have a break since there will be purges of inactives every 4 weeks.",
            "You are responsible for your own actions. It is on you to recognise when to stop; take a break from or leave a discussion.",
            "This is not a dating server. You will be warned if you cause any unnecessary and consistent discomfort.",
            "Be respectful and non-toxic. We're all humans, remember that."
        ]

        i = 1
        for guideline in guidelines:
            embed.add_field(name = "#" + str(i), value = guideline, inline = False)
            i += 1

        # embed.set_footer(text="note: not following these rules will result in a warning/ban")
        await ctx.send(embed = embed)


    @commands.group()
    async def rules(self, ctx, numbers : commands.Greedy[int] = None):
        if numbers is not None:
            numbers = [x-1 for x in numbers]

        with db:
            settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
            await ctx.send(embed = settings.get_rules_embed(orders = numbers))


    @commands.group()
    async def rule(self, ctx):
        pass

    @rule.command()
    @commands.has_permissions(manage_guild = True)
    async def add(self, ctx,*, text):
        with db:
            settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
            order = 0
            last_rule = settings.rules.order_by(Rule.order.desc()).first()
            if last_rule is not None:
                order = last_rule.order + 1

            Rule.create(settings = settings, text = text, order = order)
            await ctx.send("OK")


    @rule.command()
    @commands.has_permissions(manage_guild = True)
    async def edit(self, ctx,  number : int, *, text):
        with db:
            rule = Rule.get(order = number-1)
            rule.text = text
            rule.save()
            await ctx.send("OK")


    @rule.command()
    @commands.has_permissions(manage_guild = True)
    async def remove(self,  number : int, ctx):
        with db:
            rule = Rule.get(order = number-1)
            rule.delete_instance()
            
            settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)

            i = 0
            for rule in list(settings.rules.order_by(Rule.order)):
                rule.order = i
                rule.save()
                i += 1
 
            await ctx.send("OK")




def setup(bot):
    bot.add_cog(Management(bot))