import datetime
import random

import peewee
import discord
from discord.ext import commands, tasks

from src.discord.helpers.waiters import *
from src.models import Giveaway, Settings, database
import src.config as config

class GiveawayCog(commands.Cog, name = "Giveaway"):
    participate_emoji = "✅"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.production:
            self.poller.start()

    @commands.group(name = "giveaway")
    async def giveaway_group(self, ctx):
        pass

    @giveaway_group.command(name = "create")
    async def giveaway_create(self, ctx):
        settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
        channel = settings.get_channel("giveaway")

        giveaway = Giveaway(user_id = ctx.author.id, guild_id = ctx.guild.id, channel_id = channel.id)

        await ctx.send(ctx.translate("check_dms"))

        ctx.channel = ctx.author.dm_channel
        if ctx.channel is None:
            ctx.channel = await ctx.author.create_dm()

        await giveaway.editor_for(ctx, "title")
        await giveaway.editor_for(ctx, "key")
        # await giveaway.editor_for(ctx, "role_id_needed")
        # await giveaway.editor_for(ctx, "anonymous")
        # await giveaway.editor_for(ctx, "due_date")
        giveaway.due_date = datetime.datetime.utcnow() + datetime.timedelta(minutes = 5)

        embed = discord.Embed(color = ctx.guild_color)
        if not giveaway.anonymous:
            embed.set_author(icon_url = ctx.author.avatar_url, name = f"Giveaway by {ctx.author}")

        embed.title = giveaway.title

        embed.set_footer(text = "Due at")
        embed.timestamp = giveaway.due_date

        message = await channel.send(embed = embed)
        asyncio.gather(message.add_reaction(self.participate_emoji))

        giveaway.message_id = message.id

        giveaway.save()
        await ctx.success(ctx.translate("giveaway_created"))


    @tasks.loop(minutes = 5)
    async def poller(self):
        with database.connection_context():
            query = Giveaway.select()
            query = query.where(Giveaway.finished == False)
            query = query.where(Giveaway.due_date <= datetime.datetime.utcnow())
            for giveaway in query:
                channel = giveaway.channel
                message = await channel.fetch_message(giveaway.message_id)

                reaction = [x for x in message.reactions if str(x.emoji) == self.participate_emoji][0]
                role_needed = giveaway.guild.get_role(778744417322139689)
                participants = [x for x in await reaction.users().flatten() if role_needed is None or role_needed in x.roles]
                winner = random.choice(participants)

                print(f"winner: {winner}")
                # giveaway.finished = True
                # giveaway.save()
def setup(bot):
    bot.add_cog(GiveawayCog(bot))