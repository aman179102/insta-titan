"""Core module tests for InstaAuto"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_loader import load_config
from src.db.models import Database, PostQueue, PostedHistory


class TestConfig:
    def test_load_config(self):
        config = load_config()
        assert config is not None
        assert "app" in config
        assert "instagram" in config
        assert "scheduler" in config
        assert "sources" in config
        assert "filters" in config
        assert "web_ui" in config

    def test_config_keys(self):
        config = load_config()
        assert config["app"]["name"] == "InstaAuto"
        assert config["scheduler"]["max_posts_per_day"] >= 1
        assert isinstance(config["instagram"]["accounts"], list)


class TestDatabase:
    @pytest.fixture
    def db(self):
        return Database(":memory:")

    def test_create_db(self, db):
        assert db is not None
        assert db.engine is not None

    def test_add_to_queue(self, db):
        entry = db.add_to_queue(
            image_path="/tmp/test.jpg",
            caption="Test caption",
            source="test_source",
            tags=["nature", "landscape"],
        )
        assert entry.id is not None
        assert entry.image_path == "/tmp/test.jpg"
        assert entry.source == "test_source"
        assert entry.tags == ["nature", "landscape"]
        assert entry.status == "queued"

    def test_get_queue(self, db):
        db.add_to_queue(image_path="/tmp/img1.jpg", caption="Test 1", source="src1")
        db.add_to_queue(image_path="/tmp/img2.jpg", caption="Test 2", source="src2")
        queue = db.get_queue(limit=10)
        assert len(queue) == 2

    def test_get_queue_empty(self, db):
        queue = db.get_queue(limit=10)
        assert len(queue) == 0

    def test_mark_posted(self, db):
        entry = db.add_to_queue(image_path="/tmp/test.jpg", source="test")
        result = db.mark_posted(entry.id)
        assert result is True
        posted = db.get_queue(status="posted")
        assert len(posted) >= 1
        assert db.posts_posted_today() >= 1

    def test_mark_failed(self, db):
        entry = db.add_to_queue(image_path="/tmp/test.jpg", source="test")
        result = db.mark_failed(entry.id, "Connection error")
        assert result is True
        failed = db.get_queue(status="failed")
        assert len(failed) > 0

    def test_duplicate_detection(self, db):
        db.add_to_queue(image_path="/tmp/test.jpg", source="test")
        # Mark as posted so it goes to history
        entries = db.get_queue()
        for e in entries:
            db.mark_posted(e.id)
        # Now check duplicate with same hash
        from src.utils.helpers import get_image_hash
        hash_val = get_image_hash("/tmp/test.jpg")
        if hash_val:
            assert db.is_duplicate(hash_val) is True

    def test_queue_count(self, db):
        db.add_to_queue(image_path="/tmp/a.jpg", source="a")
        db.add_to_queue(image_path="/tmp/b.jpg", source="b")
        assert db.queue_count() == 2

    def test_posts_posted_today(self, db):
        entry = db.add_to_queue(image_path="/tmp/test.jpg", source="test")
        db.mark_posted(entry.id)
        count = db.posts_posted_today()
        assert count >= 1

    def test_search_queue(self, db):
        db.add_to_queue(image_path="/tmp/nature.jpg", caption="Beautiful sunset", source="unsplash", tags=["sunset", "nature"])
        db.add_to_queue(image_path="/tmp/car.jpg", caption="Fast car", source="pexels", tags=["car", "speed"])
        results = db.search_queue("sunset")
        assert len(results) >= 1
        results = db.search_queue("car")
        assert len(results) >= 1
        results = db.search_queue("nonexistent")
        assert len(results) == 0

    def test_search_history(self, db):
        entry = db.add_to_queue(image_path="/tmp/nature.jpg", caption="Beautiful nature", source="unsplash")
        db.mark_posted(entry.id)
        results = db.search_history("nature")
        assert len(results) >= 1
        results = db.search_history("nonexistent")
        assert len(results) == 0

    def test_log_scheduler(self, db):
        db.log_scheduler("test_action", "success", "test message", "test_account", 1, 100)
        db.log_scheduler("test_action2", "failed", "error message")
        # Verify by querying the table
        from sqlalchemy import func
        session = db.get_session()
        from src.db.models import SchedulerLog
        count = session.query(func.count(SchedulerLog.id)).scalar()
        session.close()
        assert count >= 2

    def test_log_fetch(self, db):
        db.log_fetch("test_source", 10)
        from sqlalchemy import func
        from src.db.models import Source
        session = db.get_session()
        source = session.query(Source).filter(Source.name == "test_source").first()
        session.close()
        assert source is not None
        assert source.total_fetched == 10


class TestFilters:
    @pytest.fixture
    def filter_pipeline(self):
        config = load_config()
        return __import__("src.filter.content", fromlist=["FilterPipeline"]).FilterPipeline(config)

    def test_filter_nonexistent_file(self, filter_pipeline):
        ok, reason = filter_pipeline.should_post("/nonexistent/file.jpg")
        assert ok is False
        assert "not found" in reason

    def test_filter_keyword_blocked(self, filter_pipeline):
        import tempfile
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name, format="JPEG")
            f.flush()
            ok, reason = filter_pipeline.should_post(f.name, caption="This is nsfw content")
            assert ok is False
            assert "nsfw" in reason.lower() or "blocked" in reason.lower()
            import os
            os.unlink(f.name)

    def test_filter_empty_queue(self, filter_pipeline):
        result = filter_pipeline.filter_queue([])
        assert result == []


class TestAI:
    def test_ai_fallback_caption(self):
        from src.ai.engine import AIEngine
        config = load_config()
        ai = AIEngine(config)
        caption = ai._fallback_caption(["nature", "sunset"])
        assert caption is not None
        assert len(caption) > 0

    def test_ai_disabled(self):
        from src.ai.engine import AIEngine
        config = load_config()
        config["ai"]["enabled"] = False
        ai = AIEngine(config)
        caption = ai.generate_caption("/tmp/test.jpg", ["test"])
        assert caption is not None
        assert len(caption) > 0  # Should return fallback


class TestUtils:
    def test_get_image_hash(self):
        from src.utils.helpers import get_image_hash
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"test image data")
            f.flush()
            hash_val = get_image_hash(f.name)
            assert hash_val is not None
            assert len(hash_val) > 0
            os.unlink(f.name)

    def test_validate_image(self):
        from src.utils.helpers import validate_image
        assert validate_image("/nonexistent.jpg") is False
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            from PIL import Image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name, format="JPEG")
            f.flush()
            assert validate_image(f.name, min_width=50, min_height=50) is True
            os.unlink(f.name)

    def test_human_friendly_time(self):
        from src.utils.helpers import human_friendly_time
        assert "h" in human_friendly_time(3600)
        assert "m" in human_friendly_time(60)
        assert "s" in human_friendly_time(1)

    def test_generate_caption_variation(self):
        from src.utils.helpers import generate_caption_variation
        result = generate_caption_variation("Test")
        assert "Test" in result

    def test_sanitize_filename(self):
        from src.utils.helpers import sanitize_filename
        result = sanitize_filename("hello world!@#")
        assert "hello" in result
        assert "world" in result
        assert result == result.strip()
