import re
import json

import discord
from discord.ext import commands

import src.config as config
from src.models import Settings, EmojiUsage, NamedEmbed, database as db

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
        if not self.bot.production:
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
        if not self.bot.production:
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

            embed = discord.Embed(color = ctx.guild_color )
            embed.description = ""

            for usage in emoji_usages[-10:-1]:
                embed.description += f"{usage.emoji} = {usage.total_uses}\n"

            await ctx.send(embed = embed)


    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def embed(self, ctx, name):
        if len(ctx.message.attachments) > 0:
            attachment = ctx.message.attachments[0]
            data = json.loads(await attachment.read())

            embed_data = data["embeds"][0]
            embed = discord.Embed.from_dict(embed_data)
            await ctx.send(embed = embed)

            named_embed, _ = NamedEmbed.get_or_create(name = name)
            named_embed.data = embed_data
            named_embed.save()
        else:
            try:
                named_embed = NamedEmbed.get(name = name)
            except NamedEmbed.DoesNotExist:
                await ctx.send("This embed does not exist")
            else:
                await ctx.send(embed = named_embed.embed)

    @commands.command()
    @commands.has_guild_permissions(administrator = True)
    async def resetchannel(self, ctx, channel : discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        await channel.clone()
        await channel.delete()


    @commands.command()
    async def guidelines(self, ctx, numbers : commands.Greedy[int] = None):
        with db:
            named_embed = NamedEmbed.get(name = "guidelines")
            
        if numbers is not None:
            embed = named_embed.get_embed_only_selected_fields([x-1 for x in numbers])
        else:
            embed = named_embed.embed

        await ctx.send(embed = embed)


    @commands.command()
    async def rules(self, ctx, numbers : commands.Greedy[int] = None):
        with db:
            named_embed = NamedEmbed.get(name = "rules")

        if numbers is not None:
            embed = named_embed.get_embed_only_selected_fields([x-1 for x in numbers])
        else:
            embed = named_embed.embed

        await ctx.send(embed = embed)


    # @commands.is_owner()
    # @commands.command()
    # async def clearperms(self, ctx):
    #     for role in ctx.guild.roles:

    #         if role.id not in (742246061388726272, 742245976731025459, 744687672831770656, 742178843372027934):
    #             await role.edit(permissions = discord.Permissions.none() )
    #             print("cleared", role.name, role.id)
    #         else:
    #             print("ignored", role.name, role.id)
                

    #         if role.id in (742245305772146778,):
    #             break




def setup(bot):
    bot.add_cog(Management(bot))