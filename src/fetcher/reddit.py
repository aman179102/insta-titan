import os
import praw
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class RedditFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.reddit_config = config.get("sources", {}).get("reddit", {})
        self._client = None

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def client(self):
        if self._client is None:
            c = self.reddit_config
            if c.get("client_id") and c.get("client_secret"):
                self._client = praw.Reddit(
                    client_id=c["client_id"],
                    client_secret=c["client_secret"],
                    user_agent=c.get("user_agent", "InstaAuto/1.0")
                )
        return self._client

    def fetch(self) -> List[dict]:
        results = []
        if not self.reddit_config.get("enabled") or not self.client:
            return results
        subreddits = self.reddit_config.get("subreddits", [])
        sort = self.reddit_config.get("sort", "top")
        time_filter = self.reddit_config.get("time_filter", "week")
        limit = self.reddit_config.get("limit", 50)
        min_score = self.reddit_config.get("min_score", 0)
        for sub_name in subreddits:
            try:
                subreddit = self.client.subreddit(sub_name)
                method = getattr(subreddit, sort, subreddit.hot)
                kwargs = {"limit": limit}
                if sort == "top":
                    kwargs["time_filter"] = time_filter
                for post in method(**kwargs):
                    if post.score < min_score:
                        continue
                    if not hasattr(post, 'url') or not post.url:
                        continue
                    url = post.url.lower()
                    if not any(url.endswith(e) for e in ('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                        if 'imgur.com' in url and not url.endswith('.gifv'):
                            url = post.url + '.jpg' if not post.url.endswith(('.jpg', '.png')) else post.url
                        else:
                            continue
                    caption = post.title if hasattr(post, 'title') else ""
                    tags = [sub_name]
                    if hasattr(post, 'link_flair_text') and post.link_flair_text:
                        tags.append(post.link_flair_text)
                    result = self.download_image(
                        url=post.url,
                        caption=caption,
                        tags=tags,
                        source_url=f"https://reddit.com{post.permalink}" if hasattr(post, 'permalink') else ""
                    )
                    if result:
                        results.append(result)
                logger.info(f"Reddit/{sub_name}: Fetched posts")
            except Exception as e:
                logger.error(f"Reddit/{sub_name} error: {e}")
        self.add_to_db(results)
        return results
