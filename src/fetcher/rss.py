import re
import feedparser
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger
from bs4 import BeautifulSoup


class RSSFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.rss_config = config.get("sources", {}).get("rss", {})

    @property
    def name(self) -> str:
        return "rss"

    def fetch(self) -> List[dict]:
        results = []
        if not self.rss_config.get("enabled"):
            return results
        feeds = self.rss_config.get("feeds", [])
        limit = self.rss_config.get("limit", 20)
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:limit]:
                    image_url = self._extract_image(entry)
                    if not image_url:
                        continue
                    caption = entry.get("title", "")
                    tags = []
                    if hasattr(entry, "tags"):
                        tags = [t.get("term", "") for t in entry.tags[:5] if t.get("term")]
                    result = self.download_image(
                        url=image_url,
                        caption=caption,
                        tags=tags,
                        source_url=entry.get("link", ""),
                    )
                    if result:
                        results.append(result)
                logger.info(f"RSS: Fetched from {feed_url}")
            except Exception as e:
                logger.error(f"RSS error ({feed_url}): {e}")
        self.add_to_db(results)
        return results

    def _extract_image(self, entry) -> str:
        if hasattr(entry, "media_content") and entry.media_content:
            for media in entry.media_content:
                url = media.get("url", "")
                if url:
                    return url
        if hasattr(entry, "links"):
            for link in entry.links:
                if link.get("type", "").startswith("image"):
                    return link.get("href", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        if summary:
            soup = BeautifulSoup(summary, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return img["src"]
        content = entry.get("content", [])
        for c in content:
            if hasattr(c, "value"):
                soup = BeautifulSoup(c.value, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    return img["src"]
        return ""
