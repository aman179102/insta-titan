import os
import requests
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from src.utils.helpers import logger, ensure_dir, random_delay


class BaseFetcher(ABC):
    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db
        self.download_dir = self._get_download_dir()
        ensure_dir(self.download_dir)

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fetch(self) -> List[dict]:
        pass

    def _get_download_dir(self) -> str:
        base = self.config.get("app", {}).get("data_dir", "data")
        return os.path.join(base, "downloads", self.name)

    def download_image(self, url: str, caption: str = "", tags: list = None,
                       source_url: str = "") -> Optional[dict]:
        try:
            if not url:
                return None
            ext = self._get_extension(url)
            if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'):
                ext = '.jpg'
            filename = hashlib.md5(url.encode()).hexdigest() + ext
            filepath = os.path.join(self.download_dir, filename)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                return self._make_result(filepath, caption, tags, source_url)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            resp = requests.get(url, headers=headers, timeout=30, stream=True)
            if resp.status_code != 200:
                return None
            ensure_dir(self.download_dir)
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if os.path.getsize(filepath) < 1000:
                os.remove(filepath)
                return None
            return self._make_result(filepath, caption, tags, source_url)
        except Exception as e:
            logger.error(f"Download failed: {url[:50]}... - {e}")
            return None

    def _make_result(self, filepath: str, caption: str = "", tags: list = None,
                     source_url: str = "") -> dict:
        return {
            "image_path": filepath,
            "caption": caption or "",
            "tags": tags or [],
            "source": self.name,
            "source_url": source_url or "",
        }

    def add_to_db(self, results: List[dict]):
        if not self.db or not results:
            return
        count = 0
        for r in results:
            try:
                if os.path.exists(r["image_path"]):
                    self.db.add_to_queue(
                        image_path=r["image_path"],
                        caption=r["caption"],
                        source=r["source"],
                        source_url=r.get("source_url", ""),
                        tags=r.get("tags", []),
                    )
                    count += 1
            except Exception as e:
                logger.error(f"DB add failed: {e}")
        if count > 0:
            self.db.log_fetch(self.name, count)
            logger.info(f"{self.name}: Added {count} images to queue")

    def _get_extension(self, url: str) -> str:
        path = url.split('?')[0].lower()
        for ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.heic', '.heif'):
            if path.endswith(ext):
                return ext
        _, ext = os.path.splitext(path)
        return ext if ext else '.jpg'
