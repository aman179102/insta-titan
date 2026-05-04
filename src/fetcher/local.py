import os
from typing import List
from .base import BaseFetcher
from src.utils.helpers import logger


class LocalFetcher(BaseFetcher):
    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self.local_config = config.get("sources", {}).get("local", {})

    @property
    def name(self) -> str:
        return "local"

    def fetch(self) -> List[dict]:
        results = []
        if not self.local_config.get("enabled"):
            return results
        path = self.local_config.get("path", "./images")
        recursive = self.local_config.get("recursive", True)
        valid_exts = self.local_config.get("valid_extensions",
                                           [".jpg", ".jpeg", ".png", ".webp", ".bmp"])
        if not os.path.exists(path):
            logger.warning(f"Local path not found: {path}")
            return results
        valid_exts = [e.lower() for e in valid_exts]
        for root, dirs, files in os.walk(path) if recursive else [(path, [], os.listdir(path))]:
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in valid_exts:
                    filepath = os.path.join(root, fname)
                    result = self._make_result(
                        filepath=filepath,
                        caption=os.path.splitext(fname)[0],
                        tags=["local"],
                        source_url="",
                    )
                    results.append(result)
        logger.info(f"Local: Found {len(results)} images in {path}")
        self.add_to_db(results)
        return results
