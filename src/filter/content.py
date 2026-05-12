import os
import re
from typing import List, Optional, Callable, Tuple
from src.utils.helpers import logger, get_image_hash, get_image_dimensions, validate_image


class FilterPipeline:
    def __init__(self, config: dict, db=None):
        self.config = config.get("filters", {})
        self.db = db
        self.filters = []
        self._build_pipeline()

    def _build_pipeline(self):
        pipeline_order = self.config.get("pipeline", ["keyword", "nsfw", "quality", "resolution", "duplicate"])
        filter_map = {
            "keyword": self._keyword_filter,
            "nsfw": self._nsfw_filter,
            "quality": self._quality_filter,
            "resolution": self._resolution_filter,
            "duplicate": self._duplicate_filter,
            "color": self._color_filter,
        }
        for name in pipeline_order:
            if name in filter_map:
                self.filters.append((name, filter_map[name]))

    def should_post(self, image_path: str, caption: str = "", tags: list = None) -> Tuple[bool, str]:
        if not os.path.exists(image_path):
            return False, "File not found"
        for name, filter_func in self.filters:
            passed, reason = filter_func(image_path, caption, tags or [])
            if not passed:
                logger.debug(f"Filter '{name}' rejected: {reason}")
                return False, f"{name}: {reason}"
        return True, ""

    def filter_queue(self, queue: list) -> list:
        passed = []
        for item in queue:
            ok, _ = self.should_post(
                item.image_path, item.caption,
                item.tags if hasattr(item, 'tags') else []
            )
            if ok:
                passed.append(item)
        return passed

    def _keyword_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        block_words = self.config.get("keywords_block", [])
        allow_words = self.config.get("keywords_allow", [])
        text = (caption + " " + " ".join(tags)).lower()
        for word in block_words:
            if word.lower() in text:
                return False, f"Blocked keyword: {word}"
        if allow_words:
            found = any(w.lower() in text for w in allow_words)
            if not found:
                return False, "No allowed keywords found"
        return True, ""

    def _nsfw_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        threshold = self.config.get("nsfw_threshold", 0.7)
        nsfw_keywords = ["nsfw", "porn", "sex", "adult", "xxx", "18+", "mature", "explicit"]
        text = (caption + " " + " ".join(tags)).lower()
        for kw in nsfw_keywords:
            if kw in text:
                return False, f"NSFW keyword: {kw}"
        return True, ""

    def _quality_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        min_score = self.config.get("min_quality_score", 3.0)
        try:
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size
            aspect = w / h if h > 0 else 1
            score = 5.0
            if w < 640 or h < 640:
                score -= 1.0
            if aspect < 0.5 or aspect > 2.0:
                score -= 1.0
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png'):
                pass
            else:
                score -= 0.5
            file_size = os.path.getsize(image_path)
            if file_size < 10000:
                score -= 1.5
            return score >= min_score, f"Quality score {score} < {min_score}" if score < min_score else ""
        except:
            return True, ""

    def _resolution_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        min_w = self.config.get("min_width", 640)
        min_h = self.config.get("min_height", 640)
        max_mb = self.config.get("max_file_size_mb", 20)
        if not validate_image(image_path, min_w, min_h, max_mb):
            w, h = get_image_dimensions(image_path)
            return False, f"Resolution {w}x{h} below {min_w}x{min_h}"
        return True, ""

    def _duplicate_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        if self.config.get("allow_duplicates", False):
            return True, ""
        if not self.db:
            return True, ""
        img_hash = get_image_hash(image_path)
        if self.db.is_duplicate(img_hash):
            return False, "Duplicate image"
        return True, ""

    def _color_filter(self, image_path: str, caption: str, tags: list) -> Tuple[bool, str]:
        dominant_colors = self.config.get("dominant_colors", [])
        if not dominant_colors:
            return True, ""
        try:
            from PIL import Image
            import colorsys
            img = Image.open(image_path).convert("RGB").resize((100, 100))
            pixels = list(img.getdata())
            r, g, b = zip(*pixels)
            avg_color = (sum(r) // len(r), sum(g) // len(g), sum(b) // len(b))
            h, s, v = colorsys.rgb_to_hsv(avg_color[0]/255, avg_color[1]/255, avg_color[2]/255)
            h = h * 360
            color_map = {
                "red": (0, 20), "orange": (20, 50), "yellow": (50, 70),
                "green": (70, 170), "blue": (170, 260), "purple": (260, 330),
            }
            matched = False
            for dc in dominant_colors:
                dc_lower = dc.lower()
                if dc_lower in color_map:
                    low, high = color_map[dc_lower]
                    if low <= h <= high:
                        matched = True
                        break
            if not matched:
                return False, f"No dominant color match"
            return True, ""
        except:
            return True, ""
