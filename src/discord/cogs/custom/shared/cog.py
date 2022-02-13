import datetime

from discord.ext import tasks

from src.discord.cogs.core import BaseCog
from src.discord.cogs.custom.shared.helpers import GuildHelper
from src.discord.cogs.custom.shared.helpers.praw_cache import PrawInstanceCache
from src.discord.helpers.embed import Embed
from src.models import Advertisement


class CustomCog(BaseCog):

    @tasks.loop(hours=1)
    async def advertisement(self):
        for advertisement in Advertisement:
            praw = PrawInstanceCache.get(advertisement.guild_id)
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
                        url=invite_url,
                        flair_id=flair_id
                    )
                except Exception as e:
                    print('Failed to submit: ', e)
                    continue

                subreddit_model.last_advertised = datetime.datetime.utcnow()
                subreddit_model.save()

                if channel:
                    embed = Embed.success(None)
                    embed.set_author(name=f"Successfully bumped to `{subreddit_model.name}`", url=submission.shortlink)
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(e)
                        continue


def setup(bot):
    bot.add_cog(CustomCog(bot))
