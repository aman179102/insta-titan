import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON, text, Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import enum

Base = declarative_base()


class PostStatus(enum.Enum):
    QUEUED = "queued"
    FETCHED = "fetched"
    PROCESSED = "processed"
    FILTERED = "filtered"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"


class PostType(enum.Enum):
    PHOTO = "photo"
    CAROUSEL = "carousel"
    REEL = "reel"
    STORY = "story"


class PostQueue(Base):
    __tablename__ = "post_queue"

    id = Column(Integer, primary_key=True)
    image_path = Column(String(500), nullable=False)
    caption = Column(Text, default="")
    source = Column(String(100), default="unknown")
    source_url = Column(String(500), default="")
    tags = Column(JSON, default=list)
    status = Column(String(20), default=PostStatus.QUEUED.value)
    post_type = Column(String(20), default=PostType.PHOTO.value)
    priority = Column(Integer, default=0)
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    image_hash = Column(String(100), default="")
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    account_username = Column(String(100), default="")
    platform = Column(String(50), default="instagram")
    error_message = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostedHistory(Base):
    __tablename__ = "posted_history"

    id = Column(Integer, primary_key=True)
    image_path = Column(String(500), nullable=False)
    image_hash = Column(String(100), nullable=False, index=True)
    caption = Column(Text, default="")
    tags = Column(JSON, default=list)
    source = Column(String(100), default="unknown")
    platform = Column(String(50), default="instagram")
    account_username = Column(String(100), default="")
    post_id = Column(String(100), default="")
    post_url = Column(String(500), default="")
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    posted_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    extra_data = Column(JSON, default=dict)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)
    config = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime, nullable=True)
    total_fetched = Column(Integer, default=0)
    total_posted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SchedulerLog(Base):
    __tablename__ = "scheduler_log"

    id = Column(Integer, primary_key=True)
    action = Column(String(100), nullable=False)
    status = Column(String(20), default="success")
    message = Column(Text, default="")
    account_username = Column(String(100), default="")
    post_id = Column(Integer, nullable=True)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class PingLog(Base):
    __tablename__ = "ping_log"

    id = Column(Integer, primary_key=True)
    status = Column(String(20), default="ok")
    response_time_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PingLog {self.status} {self.created_at}>"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    platform = Column(String(50), default="instagram")
    enabled = Column(Boolean, default=True)
    max_posts_per_day = Column(Integer, default=3)
    posts_today = Column(Integer, default=0)
    last_post_date = Column(DateTime, nullable=True)
    health_score = Column(Float, default=100.0)
    is_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime, nullable=True)
    session_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Encrypted credentials (stored in vault, not here directly)
    encrypted_password = Column(String(500), default="")


class Database:
    def __init__(self, db_path: str = "data/instaauto.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 15},
            poolclass=StaticPool,
            echo=False
        )
        try:
            with self.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
        except Exception:
            pass
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self, expire_on_commit: bool = True):
        session = self.Session()
        session.expire_on_commit = expire_on_commit
        return session

    def add_to_queue(self, image_path: str, caption: str = "", source: str = "unknown",
                     source_url: str = "", tags: list = None, priority: int = 0,
                     scheduled_at: datetime = None, account_username: str = "",
                     platform: str = "instagram", **kwargs) -> PostQueue:
        session = self.get_session(expire_on_commit=False)
        try:
            from src.utils.helpers import get_image_hash, get_image_dimensions
            w, h = get_image_dimensions(image_path)
            img_hash = get_image_hash(image_path)
            entry = PostQueue(
                image_path=image_path,
                caption=caption,
                source=source,
                source_url=source_url,
                tags=tags or [],
                priority=priority,
                scheduled_at=scheduled_at,
                image_hash=img_hash,
                width=w,
                height=h,
                file_size=os.path.getsize(image_path) if os.path.exists(image_path) else 0,
                account_username=account_username,
                platform=platform,
                **kwargs
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_queue(self, status: str = "queued", limit: int = 100) -> list:
        session = self.get_session(expire_on_commit=False)
        try:
            items = session.query(PostQueue).filter(
                PostQueue.status == status
            ).order_by(PostQueue.priority.desc(), PostQueue.created_at.asc()).limit(limit).all()
            return items
        finally:
            session.close()

    def mark_posted(self, post_id: int, post_data: dict = None) -> bool:
        session = self.get_session()
        try:
            post = session.query(PostQueue).filter(PostQueue.id == post_id).first()
            if post:
                post.status = PostStatus.POSTED.value
                post.posted_at = datetime.utcnow()
                if post_data:
                    for k, v in post_data.items():
                        setattr(post, k, v)
                history = PostedHistory(
                    image_path=post.image_path,
                    image_hash=post.image_hash,
                    caption=post.caption,
                    tags=post.tags,
                    source=post.source,
                    platform=post.platform,
                    account_username=post.account_username,
                    post_id=post_data.get("post_id", "") if post_data else "",
                    post_url=post_data.get("post_url", "") if post_data else "",
                )
                session.add(history)
                session.commit()
                return True
            return False
        except:
            session.rollback()
            return False
        finally:
            session.close()

    def mark_failed(self, post_id: int, error: str = "") -> bool:
        session = self.get_session()
        try:
            post = session.query(PostQueue).filter(PostQueue.id == post_id).first()
            if post:
                post.status = PostStatus.FAILED.value
                post.error_message = error
                post.retry_count = (post.retry_count or 0) + 1
                session.commit()
                return True
            return False
        except:
            session.rollback()
            return False
        finally:
            session.close()

    def is_duplicate(self, image_hash: str) -> bool:
        session = self.get_session()
        try:
            return session.query(PostedHistory).filter(
                PostedHistory.image_hash == image_hash
            ).first() is not None
        finally:
            session.close()

    def posts_posted_today(self, account_username: str = "") -> int:
        session = self.get_session()
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = session.query(PostedHistory).filter(PostedHistory.posted_at >= today)
            if account_username:
                query = query.filter(PostedHistory.account_username == account_username)
            return query.count()
        finally:
            session.close()

    def queue_count(self, status: str = "queued") -> int:
        session = self.get_session()
        try:
            return session.query(PostQueue).filter(PostQueue.status == status).count()
        finally:
            session.close()

    def log_scheduler(self, action: str, status: str = "success", message: str = "",
                      account: str = "", post_id: int = None, duration_ms: int = 0):
        session = self.get_session()
        try:
            entry = SchedulerLog(
                action=action, status=status, message=message,
                account_username=account, post_id=post_id, duration_ms=duration_ms
            )
            session.add(entry)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

    def log_ping(self, status: str = "ok", duration_ms: int = 0, error_message: str = ""):
        session = self.get_session()
        try:
            entry = PingLog(status=status, duration_ms=duration_ms, error_message=error_message)
            session.add(entry)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

    def get_last_ping(self):
        session = self.get_session()
        try:
            return session.query(PingLog).order_by(PingLog.created_at.desc()).first()
        finally:
            session.close()

    def log_fetch(self, source_name: str, count: int):
        session = self.get_session()
        try:
            source = session.query(Source).filter(Source.name == source_name).first()
            if source:
                source.last_fetched_at = datetime.utcnow()
                source.total_fetched = (source.total_fetched or 0) + count
            else:
                source = Source(name=source_name, source_type=source_name, total_fetched=count)
                session.add(source)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

    def search_queue(self, query: str, status: str = None) -> list:
        session = self.get_session()
        try:
            q = session.query(PostQueue)
            if status:
                q = q.filter(PostQueue.status == status)
            q = q.filter(
                (PostQueue.caption.contains(query)) |
                (PostQueue.source.contains(query)) |
                (PostQueue.tags.contains(query))
            )
            return q.order_by(PostQueue.created_at.desc()).limit(50).all()
        finally:
            session.close()

    def search_history(self, query: str) -> list:
        session = self.get_session()
        try:
            return session.query(PostedHistory).filter(
                (PostedHistory.caption.contains(query)) |
                (PostedHistory.tags.contains(query)) |
                (PostedHistory.source.contains(query))
            ).order_by(PostedHistory.posted_at.desc()).limit(50).all()
        finally:
            session.close()
