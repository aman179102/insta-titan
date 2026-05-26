"""Test security modules - vault, proxy, session encryption"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_loader import load_config
from src.security.vault import CredentialVault, ProxyManager, SessionEncryptor


class TestCredentialVault:
    @pytest.fixture
    def vault(self, tmp_path):
        vault_path = os.path.join(tmp_path, "vault.enc")
        vault = CredentialVault(vault_path=vault_path, master_key="test-key-12345")
        return vault

    def test_store_and_retrieve(self, vault):
        vault.store("instagram", {"username": "test_user", "password": "test_pass"})
        data = vault.retrieve("instagram")
        assert data["username"] == "test_user"
        assert data["password"] == "test_pass"

    def test_retrieve_nonexistent(self, vault):
        data = vault.retrieve("nonexistent")
        assert data == {}

    def test_delete(self, vault):
        vault.store("test_service", {"key": "value"})
        vault.delete("test_service")
        data = vault.retrieve("test_service")
        assert data == {}

    def test_list_services(self, vault):
        vault.store("service1", {"a": 1})
        vault.store("service2", {"b": 2})
        services = vault.list_services()
        assert "service1" in services
        assert "service2" in services

    def test_vault_path_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "subdir", "vault.enc")
            vault = CredentialVault(vault_path=vault_path, master_key="test")
            vault.store("test", {"data": "value"})
            assert os.path.exists(vault_path)


class TestProxyManager:
    @pytest.fixture
    def config(self):
        cfg = load_config()
        cfg["security"]["proxy"] = {
            "enabled": True,
            "type": "http",
            "url": "user:pass@1.2.3.4:8080",
        }
        return cfg

    def test_proxy_enabled(self, config):
        pm = ProxyManager(config)
        proxy = pm.get_proxy()
        assert "http" in proxy
        assert "https" in proxy
        assert "1.2.3.4" in proxy["http"]

    def test_proxy_disabled(self, config):
        config["security"]["proxy"]["enabled"] = False
        pm = ProxyManager(config)
        proxy = pm.get_proxy()
        assert proxy == {}

    def test_proxy_no_url(self, config):
        config["security"]["proxy"]["url"] = ""
        pm = ProxyManager(config)
        proxy = pm.get_proxy()
        assert proxy == {}


class TestSessionEncryptor:
    def test_encrypt_decrypt(self):
        original = b"test session data here"
        encrypted = SessionEncryptor.encrypt_session(original, "test-key")
        assert encrypted != original
        decrypted = SessionEncryptor.decrypt_session(encrypted, "test-key")
        assert decrypted == original

    def test_different_keys(self):
        original = b"secret data"
        encrypted = SessionEncryptor.encrypt_session(original, "key1")
        with pytest.raises(Exception):
            SessionEncryptor.decrypt_session(encrypted, "key2")
