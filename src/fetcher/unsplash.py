import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class UnsplashFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.us_config = config.get("sources", {}).get("unsplash", {})

    @property
    def name(self) -> str:
        return "unsplash"

    def fetch(self) -> List[dict]:
        results = []
        if not self.us_config.get("enabled"):
            return results
        access_key = self.us_config.get("access_key", "")
        if not access_key:
            logger.warning("Unsplash: No access_key configured")
            return results
        queries = self.us_config.get("queries", ["nature"])
        per_page = self.us_config.get("per_page", 30)
        orientation = self.us_config.get("orientation", "landscape")
        for query in queries:
            try:
                url = "https://api.unsplash.com/search/photos"
                params = {
                    "query": query,
                    "per_page": min(per_page, 30),
                    "orientation": orientation,
                    "client_id": access_key,
                }
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Unsplash API error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("results", []):
                    img_url = item.get("urls", {}).get("raw", "")
                    if not img_url:
                        img_url = item.get("urls", {}).get("regular", "")
                    if not img_url:
                        continue
                    description = item.get("description") or item.get("alt_description") or ""
                    tags = [t["title"] for t in item.get("tags", [])[:5]]
                    source_url = item.get("links", {}).get("html", "")
                    result = self.download_image(
                        url=img_url,
                        caption=description,
                        tags=tags + [query],
                        source_url=source_url,
                    )
                    if result:
                        results.append(result)
                logger.info(f"Unsplash: Fetched {query}")
            except Exception as e:
                logger.error(f"Unsplash error ({query}): {e}")
        self.add_to_db(results)
        return results
