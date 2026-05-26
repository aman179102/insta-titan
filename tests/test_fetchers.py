"""Test fetcher base class and orchestrator"""

import os
import sys
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_loader import load_config
from src.fetcher.base import BaseFetcher
from src.fetcher.orchestrator import FetcherOrchestrator
from src.db.models import Database


class TestBaseFetcher:
    @pytest.fixture
    def config(self):
        return load_config()

    @pytest.fixture
    def db(self):
        return Database(":memory:")

    def test_base_fetcher_init(self, config):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"

            def fetch(self):
                return []

        fetcher = TestFetcher(config)
        assert fetcher.name == "test"
        assert fetcher.download_dir is not None

    def test_download_invalid_url(self, config, db):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"
            def fetch(self):
                return []

        fetcher = TestFetcher(config, db)
        result = fetcher.download_image("")
        assert result is None

        result = fetcher.download_image("https://invalid.url/image.jpg")
        assert result is None

    def test_make_result(self, config):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"
            def fetch(self):
                return []

        fetcher = TestFetcher(config)
        result = fetcher._make_result(
            filepath="/tmp/test.jpg",
            caption="Test",
            tags=["tag1"],
            source_url="https://example.com",
        )
        assert result["image_path"] == "/tmp/test.jpg"
        assert result["caption"] == "Test"
        assert result["tags"] == ["tag1"]
        assert result["source"] == "test"
        assert result["source_url"] == "https://example.com"

    def test_get_extension(self, config):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"
            def fetch(self):
                return []

        fetcher = TestFetcher(config)
        assert fetcher._get_extension("https://example.com/image.jpg") == ".jpg"
        assert fetcher._get_extension("https://example.com/image.png?w=800") == ".png"
        assert fetcher._get_extension("https://example.com/image") == ".jpg"

    def test_add_to_db(self, config, db):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"
            def fetch(self):
                return []

        fetcher = TestFetcher(config, db)
        # Should not crash with empty results
        fetcher.add_to_db([])

        # Should not crash with non-existent files
        fetcher.add_to_db([{"image_path": "/nonexistent.jpg", "caption": "", "tags": [], "source": "test", "source_url": ""}])

    def test_add_to_db_with_valid_file(self, config, db):
        class TestFetcher(BaseFetcher):
            @property
            def name(self):
                return "test"
            def fetch(self):
                return []

        fetcher = TestFetcher(config, db)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            from PIL import Image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name, format="JPEG")
            f.flush()
            results = [{
                "image_path": f.name,
                "caption": "Test",
                "tags": ["tag1"],
                "source": "test",
                "source_url": "",
            }]
            fetcher.add_to_db(results)
            os.unlink(f.name)

        queue = db.get_queue()
        assert len(queue) >= 1


class TestOrchestrator:
    @pytest.fixture
    def config(self):
        return load_config()

    @pytest.fixture
    def db(self):
        return Database(":memory:")

    def test_orchestrator_init(self, config, db):
        orch = FetcherOrchestrator(config, db)
        assert orch is not None
        assert len(orch.fetchers) > 0

    def test_source_names(self, config, db):
        orch = FetcherOrchestrator(config, db)
        names = orch.get_source_names()
        assert "reddit" in names
        assert "unsplash" in names
        assert "pexels" in names
        assert "local" in names
        assert "rss" in names

    def test_fetch_all_disabled(self, config, db):
        """All sources disabled by default, fetch should return 0"""
        for source_type in config["sources"]:
            if isinstance(config["sources"][source_type], dict):
                config["sources"][source_type]["enabled"] = False
        orch = FetcherOrchestrator(config, db)
        count = orch.fetch_all()
        assert count == 0

    def test_fetch_unknown_source(self, config, db):
        orch = FetcherOrchestrator(config, db)
        count = orch.fetch_source("nonexistent_source")
        assert count == 0

    def test_fetch_local_empty(self, config, db):
        """Local source with empty directory should work"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config["sources"]["local"]["enabled"] = True
            config["sources"]["local"]["path"] = tmpdir
            orch = FetcherOrchestrator(config, db)
            count = orch.fetch_source("local")
            assert count == 0
