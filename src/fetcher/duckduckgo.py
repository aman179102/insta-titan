import requests
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class DuckDuckGoFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.ddg_config = config.get("sources", {}).get("duckduckgo", {})

    @property
    def name(self) -> str:
        return "duckduckgo"

    def fetch(self) -> List[dict]:
        results = []
        if not self.ddg_config.get("enabled"):
            return results
        queries = self.ddg_config.get("queries", ["nature photography"])
        per_page = self.ddg_config.get("per_page", 30)
        for query in queries:
            try:
                url = "https://duckduckgo.com/i.js"
                params = {
                    "q": query,
                    "s": 0,
                    "o": "json",
                    "vqd": self._get_vqd(query),
                    "f": "",
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Referer": "https://duckduckgo.com/",
                }
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"DuckDuckGo error: {resp.status_code}")
                    continue
                data = resp.json()
                for item in data.get("results", [])[:per_page]:
                    img_url = item.get("image", "")
                    if not img_url:
                        continue
                    caption = item.get("title", "")
                    result = self.download_image(
                        url=img_url,
                        caption=caption,
                        tags=[query],
                        source_url=item.get("url", ""),
                    )
                    if result:
                        results.append(result)
                logger.info(f"DuckDuckGo: Fetched {query}")
            except Exception as e:
                logger.error(f"DuckDuckGo error ({query}): {e}")
        self.add_to_db(results)
        return results

    def _get_vqd(self, query: str) -> str:
        try:
            url = "https://duckduckgo.com/"
            params = {"q": query}
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            import re
            match = re.search(r'vqd=([\d-]+)\&', resp.text)
            if match:
                return match.group(1)
        except:
            pass
        return ""
