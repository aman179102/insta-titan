import os
import hashlib
import json
import logging
import random
import string
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image
import imghdr
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("InstaAuto")


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(getattr(logging, level.upper(), logging.INFO))
    return log


def get_image_hash(image_path: str) -> str:
    try:
        with open(image_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return ""


def get_image_dimensions(image_path: str) -> tuple:
    try:
        with Image.open(image_path) as img:
            return img.size
    except:
        return (0, 0)


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def generate_caption_variation(base_caption: str, templates: list = None) -> str:
    if templates is None:
        templates = [
            "{caption}",
            "{caption} 🌟",
            "{caption} 🔥",
            "{caption} ✨",
            "{caption} 📸",
            "Check this out! {caption}",
            "Beautiful! {caption}",
            "Amazing shot! {caption}",
            "{caption} #photography",
            "{caption} #naturelovers",
        ]
    template = random.choice(templates)
    return template.format(caption=base_caption)


def get_random_hashtags(tags: list, count: int = 10) -> list:
    if len(tags) <= count:
        return tags
    return random.sample(tags, count)


def validate_image(image_path: str, min_width: int = 640, min_height: int = 640, max_size_mb: int = 20) -> bool:
    if not os.path.exists(image_path):
        return False
    file_size = os.path.getsize(image_path)
    if file_size > max_size_mb * 1024 * 1024:
        return False
    img_type = imghdr.what(image_path)
    if img_type not in ('jpeg', 'png', 'webp', 'bmp', 'gif'):
        return False
    w, h = get_image_dimensions(image_path)
    if w < min_width or h < min_height:
        return False
    return True


def human_friendly_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()

def get_file_size_mb(filepath: str) -> float:
    """Get file size in megabytes."""
    return os.path.getsize(filepath) / (1024 * 1024)

def is_supported_format(ext: str) -> bool:
    """Check if file extension is a supported image format."""
    return ext.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')
