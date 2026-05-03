import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class PexelsFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.px_config = config.get("sources", {}).get("pexels", {})

    @property
    def name(self) -> str:
        return "pexels"

    def fetch(self) -> List[dict]:
        results = []
        if not self.px_config.get("enabled"):
            return results
        api_key = self.px_config.get("api_key", "")
        if not api_key:
            logger.warning("Pexels: No api_key configured")
            return results
        queries = self.px_config.get("queries", ["nature"])
        per_page = self.px_config.get("per_page", 30)
        headers = {"Authorization": api_key}
        for query in queries:
            try:
                url = "https://api.pexels.com/v1/search"
                params = {"query": query, "per_page": min(per_page, 80)}
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Pexels API error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("photos", []):
                    img_url = item.get("src", {}).get("original", "") or item.get("src", {}).get("large2x", "")
                    if not img_url:
                        continue
                    alt = item.get("alt", "") or ""
                    photographer = item.get("photographer", "")
                    tags = [query]
                    source_url = item.get("url", "")
                    result = self.download_image(
                        url=img_url,
                        caption=alt or f"Photo by {photographer}" if photographer else "",
                        tags=tags,
                        source_url=source_url,
                    )
                    if result:
                        results.append(result)
                logger.info(f"Pexels: Fetched {query}")
            except Exception as e:
                logger.error(f"Pexels error ({query}): {e}")
        self.add_to_db(results)
        return results
