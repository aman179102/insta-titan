import random
import time
from typing import List, Optional
from src.utils.helpers import logger, random_delay


class SocialAutomation:
    def __init__(self, config: dict, poster=None, db=None):
        self.config = config
        self.poster = poster
        self.db = db

    def auto_follow(self, username: str, target_usernames: List[str], max_follows: int = 20):
        cl = self.poster._get_client(username) if self.poster else None
        if not cl:
            logger.error("Social: No client available")
            return 0
        count = 0
        for target in target_usernames[:max_follows]:
            try:
                user_id = cl.user_id_from_username(target)
                cl.user_follow(user_id)
                count += 1
                logger.info(f"Social: Followed {target}")
                random_delay(30, 60)
            except Exception as e:
                logger.error(f"Social: Follow failed for {target}: {e}")
        return count

    def auto_unfollow(self, username: str, max_unfollows: int = 20):
        cl = self.poster._get_client(username) if self.poster else None
        if not cl:
            return 0
        count = 0
        try:
            following = cl.user_following(cl.user_id)
            for user_id in list(following.keys())[:max_unfollows]:
                try:
                    cl.user_unfollow(user_id)
                    count += 1
                    logger.info(f"Social: Unfollowed {user_id}")
                    random_delay(30, 60)
                except:
                    continue
        except Exception as e:
            logger.error(f"Social: Unfollow error - {e}")
        return count

    def auto_like(self, username: str, hashtags: List[str], max_likes: int = 30):
        cl = self.poster._get_client(username) if self.poster else None
        if not cl:
            return 0
        count = 0
        for tag in hashtags:
            try:
                medias = cl.hashtag_medias_recent(tag, 20)
                for media in medias:
                    if count >= max_likes:
                        break
                    try:
                        cl.media_like(media.id)
                        count += 1
                        logger.info(f"Social: Liked {media.id}")
                        random_delay(20, 40)
                    except:
                        continue
            except Exception as e:
                logger.error(f"Social: Like error for {tag}: {e}")
        return count

    def auto_comment(self, username: str, hashtags: List[str], comments: List[str], max_comments: int = 10):
        cl = self.poster._get_client(username) if self.poster else None
        if not cl:
            return 0
        count = 0
        for tag in hashtags:
            try:
                medias = cl.hashtag_medias_recent(tag, 10)
                for media in medias:
                    if count >= max_comments:
                        break
                    try:
                        comment = random.choice(comments)
                        cl.media_comment(media.id, comment)
                        count += 1
                        logger.info(f"Social: Commented on {media.id}")
                        random_delay(60, 120)
                    except:
                        continue
            except Exception as e:
                logger.error(f"Social: Comment error for {tag}: {e}")
        return count
