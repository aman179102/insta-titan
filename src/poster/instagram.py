import os
import pickle
import time
import random
from datetime import datetime
from typing import Optional, List
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, PleaseWaitFewMinutes,
    TwoFactorRequired, ClientError
)
from src.utils.helpers import logger, random_delay


class InstagramPoster:
    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db
        self.insta_config = config.get("instagram", {})
        self.clients = {}
        self.session_dir = self.insta_config.get("session_dir", "sessions")
        os.makedirs(self.session_dir, exist_ok=True)

    def _get_client(self, username: str) -> Optional[Client]:
        if username in self.clients:
            try:
                self.clients[username].get_timeline_feed()
                return self.clients[username]
            except:
                pass
        cl = Client()
        cl.delay_range = [3, 8]
        proxy_cfg = self.config.get("security", {}).get("proxy", {})
        if proxy_cfg.get("enabled") and proxy_cfg.get("url"):
            cl.set_proxy(proxy_cfg["url"])
        session_path = os.path.join(self.session_dir, f"{username}.session")
        if os.path.exists(session_path):
            try:
                with open(session_path, "rb") as f:
                    cl = pickle.load(f)
                cl.delay_range = [3, 8]
                cl.get_timeline_feed()
                self.clients[username] = cl
                logger.info(f"Instagram: Session loaded for {username}")
                return cl
            except Exception as e:
                logger.warning(f"Instagram: Session expired for {username}: {e}")
                os.remove(session_path)
        for account in self.insta_config.get("accounts", []):
            if account.get("username") == username:
                password = account.get("password", "")
                if not password:
                    logger.error(f"Instagram: No password for {username}")
                    return None
                try:
                    cl.login(username, password)
                    with open(session_path, "wb") as f:
                        pickle.dump(cl, f)
                    self.clients[username] = cl
                    logger.info(f"Instagram: Logged in as {username}")
                    return cl
                except ChallengeRequired:
                    logger.error(f"Instagram: Challenge required for {username}")
                    challenge = cl.challenge_resolve(cl.last_json)
                    if challenge:
                        with open(session_path, "wb") as f:
                            pickle.dump(cl, f)
                        self.clients[username] = cl
                        return cl
                except TwoFactorRequired:
                    logger.error("Instagram: 2FA required")
                except PleaseWaitFewMinutes as e:
                    logger.error(f"Instagram: Rate limited - {e}")
                except Exception as e:
                    logger.error(f"Instagram: Login failed for {username}: {e}")
                return None

    def post_photo(self, image_path: str, caption: str = "",
                   username: str = "", account_config: dict = None) -> Optional[dict]:
        cl = self._get_client(username)
        if not cl:
            return None
        try:
            account = account_config or self._get_account_config(username)
            if account:
                today = datetime.utcnow().date()
                last_post = account.get("last_post_date")
                if last_post and last_post.date() == today:
                    posts_today = account.get("posts_today", 0)
                else:
                    posts_today = 0
                    account["posts_today"] = 0
                max_posts = account.get("max_posts_per_day", 3)
                if posts_today >= max_posts:
                    logger.warning(f"Instagram: {username} reached daily limit ({max_posts})")
                    return None
            media = cl.photo_upload(image_path, caption)
            result = {
                "post_id": str(media.id),
                "post_url": f"https://instagram.com/p/{media.code}/",
                "posted_at": datetime.utcnow(),
            }
            if account:
                account["posts_today"] = account.get("posts_today", 0) + 1
                account["last_post_date"] = datetime.utcnow()
            logger.info(f"Instagram: Posted {media.code}")
            random_delay(2, 5)
            return result
        except LoginRequired:
            logger.error("Instagram: Login required, reconnecting...")
            if username in self.clients:
                del self.clients[username]
            session_path = os.path.join(self.session_dir, f"{username}.session")
            if os.path.exists(session_path):
                os.remove(session_path)
            return self.post_photo(image_path, caption, username, account_config)
        except PleaseWaitFewMinutes as e:
            logger.error(f"Instagram: Rate limited - waiting... {e}")
            return None
        except Exception as e:
            logger.error(f"Instagram: Upload error - {e}")
            return None

    def _get_account_config(self, username: str) -> Optional[dict]:
        for acc in self.insta_config.get("accounts", []):
            if acc.get("username") == username:
                return acc
        return None

    def check_health(self, username: str) -> float:
        try:
            cl = self._get_client(username)
            if not cl:
                return 0.0
            user_id = cl.user_id
            info = cl.user_info(user_id)
            score = 100.0
            if info.is_verified:
                score -= 5
            if info.follower_count < 10:
                score -= 20
            if info.following_count > info.follower_count * 5:
                score -= 15
            return score
        except:
            return 0.0

def refresh_session(self, username: str) -> bool:
    """Force refresh Instagram session with exponential backoff."""
    if username in self.clients:
        del self.clients[username]
    session_path = os.path.join(self.session_dir, f"{username}.session")
    if os.path.exists(session_path):
        os.remove(session_path)
    cl = self._get_client(username)
    return cl is not None
