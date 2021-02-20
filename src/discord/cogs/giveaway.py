import datetime
import random

import peewee
import discord
from discord.ext import commands, tasks

from src.discord.helpers.waiters import *
from src.models import Giveaway, Settings, database
import src.config as config
from src.discord.cogs.core import BaseCog

class GiveawayCog(BaseCog, name = "Giveaway"):
    participate_emoji = "✅"

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.poller, check = self.bot.production)

    @commands.guild_only()
    @commands.group(name = "giveaway")
    async def giveaway_group(self, ctx):
        pass

    @giveaway_group.command(name = "create")
    async def giveaway_create(self, ctx):
        settings, _ = Settings.get_or_create(guild_id = ctx.guild.id)
        channel = settings.get_channel("giveaway")

        giveaway = Giveaway(user_id = ctx.author.id, guild_id = ctx.guild.id, channel_id = channel.id)
        #TODO: make this non server specific.
        waiter = BoolWaiter(ctx, prompt = "Restrict to 5k+ role?")
        if ctx.guild.id == 742146159711092757 and await waiter.wait():
            giveaway.role_id_needed = 778744417322139689

        await ctx.send(ctx.translate("check_dms"))

        ctx.channel = ctx.author.dm_channel
        if ctx.channel is None:
            ctx.channel = await ctx.author.create_dm()

        await giveaway.editor_for(ctx, "title")
        await giveaway.editor_for(ctx, "amount")
        if giveaway.amount == 1:
            await giveaway.editor_for(ctx, "key")
        await giveaway.editor_for(ctx, "due_date")

        giveaway.save()

        message = await channel.send(embed = giveaway.get_embed())
        asyncio.gather(message.add_reaction(self.participate_emoji))
        giveaway.message_id = message.id
        giveaway.save()

        await ctx.success(ctx.translate("giveaway_created"))

    @tasks.loop(seconds = 30)
    async def poller(self):
        with database.connection_context():
            query = Giveaway.select()
            query = query.where(Giveaway.finished == False)
            query = query.where(Giveaway.due_date <= datetime.datetime.utcnow())
            # query = [Giveaway.get(id = 10)]
            for giveaway in query:
                channel = giveaway.channel
                message = await channel.fetch_message(giveaway.message_id)

                reaction = [x for x in message.reactions if str(x.emoji) == self.participate_emoji][0]
                role_needed = giveaway.role_needed
                participants = [x for x in await reaction.users().flatten() if (role_needed is None or role_needed in x.roles) and not x.bot]
                if len(participants) == 0:
                    continue

                random.shuffle(participants)
                if len(participants) >= giveaway.amount:
                    winners = participants[:giveaway.amount]
                else:
                    winners = [x for x in participants]
                    while len(winners) < giveaway.amount:
                        winners.append(random.choice(participants))

                embed = message.embeds[0]

                notes = [f"**{giveaway.title}**\n"]
                for winner in winners:
                    notes.append(f"Winner: **{winner}**")

                embed.description = "\n".join(notes)

                embed.timestamp = discord.Embed.Empty
                embed.set_footer(text = discord.Embed.Empty)
                await message.edit(embed = embed)
                for winner in winners:
                    dm_owner = giveaway.key is None

                    if not dm_owner:
                        try:
                            await winner.send(f"Congratulations, you won giveaway **{giveaway.id}**\n`{giveaway.title}`\nHere are your rewards:\n`{giveaway.key}`")
                        except discord.errors.Forbidden:
                            dm_owner = True

                    if dm_owner:
                        await giveaway.user.send(f"Giveaway **{giveaway.id}** has been won by **{winner}**. They will have to be informed and their rewards sent by you.")

                asyncio.gather(message.clear_reactions())
                giveaway.finished = True
                giveaway.save()
def setup(bot):
    bot.add_cog(GiveawayCog(bot))