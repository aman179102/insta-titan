from typing import List
from src.utils.helpers import logger
from .reddit import RedditFetcher
from .unsplash import UnsplashFetcher
from .pexels import PexelsFetcher
from .pixabay import PixabayFetcher
from .local import LocalFetcher
from .rss import RSSFetcher
from .google_images import GoogleImagesFetcher
from .bing import BingFetcher
from .duckduckgo import DuckDuckGoFetcher


class FetcherOrchestrator:
    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db
        self.fetchers = self._init_fetchers()

    def _init_fetchers(self) -> list:
        return [
            RedditFetcher(self.config, self.db),
            UnsplashFetcher(self.config, self.db),
            PexelsFetcher(self.config, self.db),
            PixabayFetcher(self.config, self.db),
            LocalFetcher(self.config, self.db),
            RSSFetcher(self.config, self.db),
            GoogleImagesFetcher(self.config, self.db),
            BingFetcher(self.config, self.db),
            DuckDuckGoFetcher(self.config, self.db),
        ]

    def fetch_all(self) -> int:
        total = 0
        for fetcher in self.fetchers:
            try:
                results = fetcher.fetch()
                total += len(results)
            except Exception as e:
                logger.error(f"Fetcher {fetcher.name} error: {e}")
        logger.info(f"Fetcher: Total {total} images fetched")
        return total

    def fetch_source(self, source_name: str) -> int:
        for fetcher in self.fetchers:
            if fetcher.name == source_name:
                results = fetcher.fetch()
                return len(results)
        logger.warning(f"Fetcher: Unknown source '{source_name}'")
        return 0

    def get_source_names(self) -> List[str]:
        return [f.name for f in self.fetchers]
