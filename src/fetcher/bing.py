import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class BingFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.bing_config = config.get("sources", {}).get("bing", {})

    @property
    def name(self) -> str:
        return "bing"

    def fetch(self) -> List[dict]:
        results = []
        if not self.bing_config.get("enabled"):
            return results
        api_key = self.bing_config.get("api_key", "")
        if not api_key:
            logger.warning("Bing: No api_key configured")
            return results
        queries = self.bing_config.get("queries", ["beautiful landscape"])
        per_page = self.bing_config.get("per_page", 30)
        for query in queries:
            try:
                url = "https://api.bing.microsoft.com/v7.0/images/search"
                headers = {"Ocp-Apim-Subscription-Key": api_key}
                params = {
                    "q": query,
                    "count": min(per_page, 150),
                    "safeSearch": "Moderate",
                }
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Bing API error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("value", []):
                    img_url = item.get("contentUrl", "")
                    if not img_url:
                        continue
                    caption = item.get("name", "")
                    tags = [query]
                    result = self.download_image(
                        url=img_url,
                        caption=caption,
                        tags=tags,
                        source_url=item.get("hostPageUrl", ""),
                    )
                    if result:
                        results.append(result)
                logger.info(f"Bing: Fetched {query}")
            except Exception as e:
                logger.error(f"Bing error ({query}): {e}")
        self.add_to_db(results)
        return results
