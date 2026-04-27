import os
import yaml
from dotenv import load_dotenv
from src.utils.helpers import logger


def load_config(path: str = "config.yaml") -> dict:
    load_dotenv(".env")
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)

        env_overrides = {
            ("instagram", "accounts", 0, "username"): "INSTA_USERNAME",
            ("instagram", "accounts", 0, "password"): "INSTA_PASSWORD",
            ("sources", "unsplash", "access_key"): "UNSPLASH_ACCESS_KEY",
            ("sources", "pexels", "api_key"): "PEXELS_API_KEY",
            ("sources", "pixabay", "api_key"): "PIXABAY_API_KEY",
            ("sources", "bing", "api_key"): "BING_API_KEY",
            ("sources", "google_images", "api_key"): "GOOGLE_IMAGES_API_KEY",
            ("sources", "google_images", "cx"): "GOOGLE_IMAGES_CX",
            ("sources", "reddit", "client_id"): "REDDIT_CLIENT_ID",
            ("sources", "reddit", "client_secret"): "REDDIT_CLIENT_SECRET",
            ("web_ui", "secret_key"): "FLASK_SECRET_KEY",
            ("notifications", "telegram", "bot_token"): "TELEGRAM_BOT_TOKEN",
            ("notifications", "telegram", "chat_id"): "TELEGRAM_CHAT_ID",
        }

        for keys, env_var in env_overrides.items():
            val = os.getenv(env_var)
            if val:
                target = config
                for key in keys[:-1]:
                    if isinstance(target, dict):
                        target = target.setdefault(key, {})
                    elif isinstance(target, list) and isinstance(key, int):
                        while len(target) <= key:
                            target.append({})
                        target = target[key]
                last_key = keys[-1]
                if isinstance(target, dict):
                    target[last_key] = val
                elif isinstance(target, list) and isinstance(last_key, int):
                    while len(target) <= last_key:
                        target.append({})
                    target[last_key] = val

        config.setdefault("app", {}).setdefault("data_dir", "data")
        config.setdefault("instagram", {}).setdefault("accounts", [])
        config.setdefault("scheduler", {}).setdefault("max_posts_per_day", 3)
        config.setdefault("sources", {})
        config.setdefault("filters", {})
        config.setdefault("processor", {})
        config.setdefault("ai", {}).setdefault("enabled", False)
        config.setdefault("notifications", {}).setdefault("enabled", True)
        config.setdefault("web_ui", {}).setdefault("enabled", True)

        logger.info(f"Config loaded from {path}")
        return config
    except Exception as e:
        logger.error(f"Config load failed: {e}")
        return {}
