from datetime import datetime, timedelta
from typing import List
from src.utils.helpers import logger


class AnalyticsTracker:
    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db

    def get_dashboard_stats(self) -> dict:
        if not self.db:
            return {}
        session = self.db.get_session()
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            from sqlalchemy import func
            from src.db.models import PostQueue, PostedHistory, SchedulerLog
            total_queued = session.query(func.count(PostQueue.id)).filter(
                PostQueue.status == "queued"
            ).scalar() or 0
            total_posted = session.query(func.count(PostedHistory.id)).scalar() or 0
            posted_today = session.query(func.count(PostedHistory.id)).filter(
                PostedHistory.posted_at >= today
            ).scalar() or 0
            posted_week = session.query(func.count(PostedHistory.id)).filter(
                PostedHistory.posted_at >= week_ago
            ).scalar() or 0
            failed = session.query(func.count(PostQueue.id)).filter(
                PostQueue.status == "failed"
            ).scalar() or 0
            recent_posts = session.query(PostedHistory).order_by(
                PostedHistory.posted_at.desc()
            ).limit(10).all()
            from src.db.models import Source
            sources = session.query(Source).all()
            source_stats = {}
            for s in sources:
                source_stats[s.name] = {
                    "total_fetched": s.total_fetched or 0,
                    "total_posted": s.total_posted or 0,
                }
            last_post = session.query(PostedHistory).order_by(
                PostedHistory.posted_at.desc()
            ).first()
            return {
                "total_queued": total_queued,
                "total_posted": total_posted,
                "posted_today": posted_today,
                "posted_week": posted_week,
                "failed": failed,
                "last_post_at": last_post.posted_at.isoformat() if last_post and last_post.posted_at else None,
                "last_post_caption": (last_post.caption or "")[:50] if last_post else None,
                "recent_posts": [
                    {
                        "id": p.id,
                        "caption": (p.caption or "")[:50],
                        "source": p.source,
                        "posted_at": p.posted_at.isoformat() if p.posted_at else "",
                        "likes": p.likes_count or 0,
                        "comments": p.comments_count or 0,
                    }
                    for p in recent_posts
                ],
                "sources": source_stats,
            }
        except Exception as e:
            logger.error(f"Analytics: Dashboard error - {e}")
            return {}
        finally:
            session.close()

    def get_performance_report(self, days: int = 30) -> dict:
        if not self.db:
            return {}
        session = self.db.get_session()
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            from src.db.models import PostedHistory
            start_date = datetime.utcnow() - timedelta(days=days)
            daily_stats = session.query(
                func.date(PostedHistory.posted_at).label("date"),
                func.count(PostedHistory.id).label("count"),
            ).filter(PostedHistory.posted_at >= start_date).group_by(
                func.date(PostedHistory.posted_at)
            ).all()
            total = sum(d.count for d in daily_stats)
            avg = total / max(len(daily_stats), 1)
            return {
                "period_days": days,
                "total_posts": total,
                "daily_average": round(avg, 1),
                "daily_breakdown": [
                    {"date": str(d.date), "count": d.count} for d in daily_stats
                ],
            }
        finally:
            session.close()
