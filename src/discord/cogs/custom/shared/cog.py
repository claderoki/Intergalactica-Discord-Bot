import datetime

from discord.ext import tasks

from src.discord.cogs.core import BaseCog
from src.models import Advertisement
from src.discord.cogs.custom.shared.helpers import GuildHelper
from src.discord.helpers.embed import Embed
from src.discord.cogs.custom.shared.helpers import Logger

class CustomCog(BaseCog):
    praw_instances = {}

    async def on_ready(self):
        self.start_task(self.advertisement, check = True)

    @tasks.loop(hours = 1)
    async def advertisement(self):
        for advertisement in Advertisement:
            praw = self.praw_instances.get(advertisement.guild_id)
            if praw is None:
                continue

            guild = advertisement.guild
            channel = guild.get_channel(advertisement.log_channel_id)

            for subreddit_model in advertisement.subreddits:
                if not subreddit_model.post_allowed:
                    continue

                subreddit = praw.subreddit(subreddit_model.name)
                invite_url = await GuildHelper.get_invite_url(guild)

                try:
                    submission = subreddit.submit(advertisement.description, url = invite_url)
                except Exception as e:
                    print(e)
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