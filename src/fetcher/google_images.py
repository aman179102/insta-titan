import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class GoogleImagesFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.gi_config = config.get("sources", {}).get("google_images", {})

    @property
    def name(self) -> str:
        return "google_images"

    def fetch(self) -> List[dict]:
        results = []
        if not self.gi_config.get("enabled"):
            return results
        queries = self.gi_config.get("queries", ["nature photography"])
        per_page = self.gi_config.get("per_page", 30)
        safe = self.gi_config.get("safe", "active")
        for query in queries:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "q": query,
                    "searchType": "image",
                    "num": min(per_page, 10),
                    "safe": safe,
                    "cx": self.gi_config.get("cx", ""),
                    "key": self.gi_config.get("api_key", ""),
                }
                if not params.get("cx") or not params.get("key"):
                    logger.warning("Google Images: cx and api_key required")
                    continue
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Google Images API error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("items", []):
                    img_url = item.get("link", "")
                    if not img_url:
                        continue
                    caption = item.get("title", "")
                    snippet = item.get("snippet", "")
                    result = self.download_image(
                        url=img_url,
                        caption=caption or snippet or "",
                        tags=[query],
                        source_url=item.get("image", {}).get("contextLink", ""),
                    )
                    if result:
                        results.append(result)
                logger.info(f"Google Images: Fetched {query}")
            except Exception as e:
                logger.error(f"Google Images error ({query}): {e}")
        self.add_to_db(results)
        return results
