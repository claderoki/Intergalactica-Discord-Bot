import datetime

from discord.ext import tasks, commands

from src.discord.cogs.custom.shared.helpers.bump_reminder import DisboardBumpReminder
from src.discord.cogs.core import BaseCog
from src.models import Advertisement
from src.discord.cogs.custom.shared.helpers import GuildHelper
from src.discord.helpers.embed import Embed

class CustomCog(BaseCog):
    praw_instances = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if DisboardBumpReminder.is_eligible(message):
            await DisboardBumpReminder.recheck_minutes(message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_task(self.advertisement, check = self.bot.production)
        self.start_task(self.bump_poller, check = self.bot.production)

    @tasks.loop(minutes = 1)
    async def bump_poller(self):
        for bump_context in DisboardBumpReminder.get_available_bumps():
            content = f"A bump is available! `{DisboardBumpReminder._cmd}` to bump."
            if bump_context.role_id is not None:
                content = f"<@&{bump_context.role_id}>, {content}"
            channel = self.bot.get_channel(bump_context.channel_id)
            last_message = channel.last_message

            if last_message is None or last_message.content != content:
                await channel.send(content)

    @tasks.loop(hours = 1)
    async def advertisement(self):
        for advertisement in Advertisement:
            praw = self.praw_instances.get(advertisement.guild_id)
            if praw is None:
                continue

            guild = advertisement.guild
            channel = guild.get_channel(advertisement.log_channel_id)

            for subreddit_model in advertisement.subreddits:
                if not subreddit_model.active:
                    continue
                if not subreddit_model.post_allowed:
                    continue

                subreddit = praw.subreddit(subreddit_model.name)
                invite_url = await GuildHelper.get_invite_url(guild)

                flair_id = None
                if subreddit_model.flair is not None:
                    for flair in subreddit.flair.link_templates:
                        if flair["text"] == subreddit_model.flair:
                            flair_id = flair["id"]

                try:
                    submission = subreddit.submit(
                      advertisement.description,
                      url = invite_url,
                      flair_id = flair_id
                    )
                except Exception as e:
                    print('Failed to submit: ', e)
                    continue

                subreddit_model.last_advertised = datetime.datetime.utcnow()
                subreddit_model.save()

                if channel:
                    embed = Embed.success(None)
                    embed.set_author(name = f"Successfully bumped to `{subreddit_model.name}`", url = submission.shortlink)
                    try:
                        await channel.send(embed = embed)
                    except Exception as e:
                        print(e)
                        continue

def setup(bot):
    bot.add_cog(CustomCog(bot))
