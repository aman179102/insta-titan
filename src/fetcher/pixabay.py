import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class PixabayFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.pb_config = config.get("sources", {}).get("pixabay", {})

    @property
    def name(self) -> str:
        return "pixabay"

    def fetch(self) -> List[dict]:
        results = []
        if not self.pb_config.get("enabled"):
            return results
        api_key = self.pb_config.get("api_key", "")
        if not api_key:
            logger.warning("Pixabay: No api_key configured")
            return results
        queries = self.pb_config.get("queries", ["nature"])
        per_page = self.pb_config.get("per_page", 30)
        image_type = self.pb_config.get("image_type", "photo")
        orientation = self.pb_config.get("orientation", "horizontal")
        safesearch = self.pb_config.get("safesearch", True)
        for query in queries:
            try:
                url = "https://pixabay.com/api/"
                params = {
                    "key": api_key,
                    "q": query,
                    "per_page": min(per_page, 200),
                    "image_type": image_type,
                    "orientation": orientation,
                    "safesearch": str(safesearch).lower(),
                }
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Pixabay API error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("hits", []):
                    img_url = item.get("largeImageURL", "") or item.get("webformatURL", "")
                    if not img_url:
                        continue
                    tags_str = item.get("tags", "")
                    tags = [t.strip() for t in tags_str.split(",")] if tags_str else [query]
                    result = self.download_image(
                        url=img_url,
                        caption=tags_str or "",
                        tags=tags,
                        source_url=item.get("pageURL", ""),
                    )
                    if result:
                        results.append(result)
                logger.info(f"Pixabay: Fetched {query}")
            except Exception as e:
                logger.error(f"Pixabay error ({query}): {e}")
        self.add_to_db(results)
        return results
