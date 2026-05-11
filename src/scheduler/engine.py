import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from src.utils.helpers import logger, human_friendly_time


class SmartScheduler:
    def __init__(self, config: dict, db=None, poster=None, processors: dict = None):
        self.config = config
        self.sched_config = config.get("scheduler", {})
        self.db = db
        self.poster = poster
        self.processors = processors or {}
        self.scheduler = BackgroundScheduler(daemon=True)
        self._running = False

    def start(self):
        if not self.sched_config.get("enabled", True):
            logger.info("Scheduler: Disabled in config")
            return
        if self._running:
            return
        posts_per_day = self.sched_config.get("max_posts_per_day", 3)
        active_start = self.sched_config.get("active_hours_start", 10)
        active_end = self.sched_config.get("active_hours_end", 22)
        warmup = self.sched_config.get("gradual_warmup", True)
        warmup_days = self.sched_config.get("warmup_days", 7)
        cooldown_on_error = self.sched_config.get("cooldown_on_error", True)
        cooldown_hours = self.sched_config.get("cooldown_hours", 24)
        self._schedule_next_post()
        self.scheduler.add_job(
            self._check_queue,
            IntervalTrigger(minutes=15),
            id="queue_check",
            name="Queue Check",
            replace_existing=True,
        )
        self.scheduler.start()
        self._running = True
        logger.info("Scheduler: Started")
        logger.info(f"Scheduler: {posts_per_day} posts/day, {active_start}:00-{active_end}:00")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler: Stopped")

    def _schedule_next_post(self):
        times = self._get_posting_times()
        for i, post_time in enumerate(times):
            self.scheduler.add_job(
                self._execute_post,
                DateTrigger(run_date=post_time),
                id=f"post_{i}_{int(post_time.timestamp())}",
                name=f"Post at {post_time.strftime('%H:%M')}",
                replace_existing=True,
            )
        if times:
            logger.info(f"Scheduler: Scheduled {len(times)} posts, next at {times[0].strftime('%H:%M')}")

    def _get_posting_times(self) -> List[datetime]:
        posts_per_day = self.sched_config.get("max_posts_per_day", 3)
        active_start = self.sched_config.get("active_hours_start", 10)
        active_end = self.sched_config.get("active_hours_end", 22)
        min_interval = self.sched_config.get("min_interval_minutes", 240)
        warmup = self.sched_config.get("gradual_warmup", True)
        warmup_days = self.sched_config.get("warmup_days", 7)
        now = datetime.now()
        if warmup:
            days_active = 1
            if self.db:
                days_active = max(1, self.db.posts_posted_today())
            warmup_factor = min(days_active / warmup_days, 1.0)
            effective_posts = max(1, int(posts_per_day * warmup_factor))
        else:
            effective_posts = posts_per_day
        effective_posts = min(effective_posts, posts_per_day)
        window_hours = active_end - active_start
        if window_hours <= 0:
            window_hours = 12
        slot_duration = (window_hours * 60) / effective_posts
        times = []
        for i in range(effective_posts):
            slot_start = now.replace(hour=active_start, minute=0, second=0, microsecond=0)
            if i > 0 and times:
                last_time = times[-1]
                min_gap = timedelta(minutes=min_interval)
                if last_time + min_gap > slot_start:
                    slot_start = last_time + min_gap
            slot_begin = slot_start + timedelta(minutes=i * slot_duration)
            slot_end = slot_begin + timedelta(minutes=slot_duration * 0.8)
            if slot_end.hour >= active_end:
                slot_end = slot_end.replace(hour=active_end, minute=0)
            if slot_begin < now:
                slot_begin = now + timedelta(minutes=10)
            if slot_begin >= slot_end:
                continue
            jitter = random.randint(0, max(1, int((slot_end - slot_begin).total_seconds() // 60)))
            post_time = slot_begin + timedelta(minutes=jitter)
            if post_time > slot_end:
                post_time = slot_end - timedelta(minutes=5)
            if post_time > now:
                times.append(post_time)
        return times[:effective_posts]

    def _check_queue(self):
        if not self.db:
            return
        queue = self.db.get_queue(status="queued", limit=5)
        if not queue:
            logger.info("Scheduler: Queue empty, triggering fetch")
            self._trigger_fetch()
        else:
            logger.info(f"Scheduler: {len(queue)} items in queue")

    def _trigger_fetch(self):
        fetcher = self.processors.get("fetcher")
        if fetcher:
            logger.info("Scheduler: Auto-fetching images...")
            try:
                count = fetcher.fetch_all()
                logger.info(f"Scheduler: Fetched {count} images")
            except Exception as e:
                logger.error(f"Scheduler: Fetch error - {e}")

    def _execute_post(self):
        start_time = time.time()
        if not self.db or not self.poster:
            logger.error("Scheduler: DB or Poster not initialized")
            return
        queue = self.db.get_queue(status="queued", limit=1)
        if not queue:
            logger.warning("Scheduler: No posts in queue to execute")
            self._trigger_fetch()
            return
        post = queue[0]
        account_username = post.account_username or self._get_default_account()
        if not account_username:
            logger.error("Scheduler: No account configured")
            return
        if self.db.posts_posted_today(account_username) >= self.sched_config.get("max_posts_per_day", 3):
            logger.info(f"Scheduler: Daily limit reached for {account_username}")
            return
        logger.info(f"Scheduler: Posting {post.id} - {post.image_path[:50]}...")
        result = self.poster.post_photo(
            image_path=post.image_path,
            caption=post.caption,
            username=account_username,
        )
        duration = int((time.time() - start_time) * 1000)
        if result:
            posted_data = {
                "post_id": result.get("post_id", ""),
                "post_url": result.get("post_url", ""),
            }
            self.db.mark_posted(post.id, posted_data)
            self.db.log_scheduler(
                action="post_photo", status="success",
                message=f"Posted {post.image_path[:50]}...",
                account=account_username, post_id=post.id, duration_ms=duration
            )
            logger.info(f"Scheduler: Posted successfully ({duration}ms)")
            self._schedule_next_post()
        else:
            self.db.mark_failed(post.id, "Upload failed")
            self.db.log_scheduler(
                action="post_photo", status="failed",
                message="Upload failed",
                account=account_username, post_id=post.id, duration_ms=duration
            )
            cooldown = self.sched_config.get("cooldown_hours", 24)
            logger.error(f"Scheduler: Post failed, cooling down for {cooldown}h")
            self.scheduler.add_job(
                self._execute_post,
                DateTrigger(run_date=datetime.now() + timedelta(hours=cooldown)),
                id=f"retry_{int(time.time())}",
                name="Retry post",
                replace_existing=True,
            )

    def _get_default_account(self) -> str:
        accounts = self.config.get("instagram", {}).get("accounts", [])
        for acc in accounts:
            if acc.get("enabled", False) and acc.get("username"):
                return acc["username"]
        return ""

    def post_now(self) -> bool:
        try:
            self._execute_post()
            return True
        except Exception as e:
            logger.error(f"Scheduler: post_now failed - {e}")
            return False

    def get_status(self) -> dict:
        jobs = self.scheduler.get_jobs()
        next_run = None
        for j in jobs:
            if j.name.startswith("Post at") and j.next_run_time:
                if not next_run or j.next_run_time < next_run:
                    next_run = j.next_run_time
        queue_count = self.db.queue_count() if self.db else 0
        return {
            "running": self._running,
            "jobs": len(jobs),
            "next_post": next_run,
            "queue_count": queue_count,
        }
