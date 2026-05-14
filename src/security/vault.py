import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from src.utils.helpers import logger


class CredentialVault:
    def __init__(self, vault_path: str = "data/vault.enc", master_key: str = None):
        self.vault_path = vault_path
        self._key = self._derive_key(master_key or "instaauto-default-key-change-me")
        self._fernet = Fernet(self._key)

    def _derive_key(self, master_key: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"instaauto-salt",
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))

    def _read_vault(self) -> dict:
        if not os.path.exists(self.vault_path):
            return {}
        file_size = os.path.getsize(self.vault_path)
        if file_size == 0:
            return {}
        try:
            with open(self.vault_path, 'rb') as f:
                return json.loads(self._fernet.decrypt(f.read()).decode())
        except Exception:
            return {}

    def _write_vault(self, data: dict):
        encrypted = self._fernet.encrypt(json.dumps(data).encode())
        os.makedirs(os.path.dirname(self.vault_path) or ".", exist_ok=True)
        with open(self.vault_path, 'wb') as f:
            f.write(encrypted)

    def store(self, service: str, credentials: dict):
        try:
            data = self._read_vault()
            data[service] = credentials
            self._write_vault(data)
            logger.info(f"Vault: Stored credentials for {service}")
        except Exception as e:
            logger.error(f"Vault: Store failed - {e}")

    def retrieve(self, service: str) -> dict:
        try:
            data = self._read_vault()
            return data.get(service, {})
        except Exception as e:
            logger.error(f"Vault: Retrieve failed - {e}")
            return {}

    def delete(self, service: str):
        try:
            data = self._read_vault()
            if service in data:
                del data[service]
                self._write_vault(data)
                logger.info(f"Vault: Deleted credentials for {service}")
        except Exception as e:
            logger.error(f"Vault: Delete failed - {e}")

    def list_services(self) -> list:
        try:
            data = self._read_vault()
            return list(data.keys())
        except:
            return []


class ProxyManager:
    def __init__(self, config: dict):
        self.config = config.get("security", {}).get("proxy", {})

    def get_proxy(self) -> dict:
        if not self.config.get("enabled"):
            return {}
        proxy_type = self.config.get("type", "http")
        url = self.config.get("url", "")
        if not url:
            return {}
        return {
            "http": f"{proxy_type}://{url}",
            "https": f"{proxy_type}://{url}",
        }

    def rotate(self):
        pass


class SessionEncryptor:
    @staticmethod
    def encrypt_session(data: bytes, key: str = "instaauto-session-key") -> bytes:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"session-salt", iterations=100000)
        fernet_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        f = Fernet(fernet_key)
        return f.encrypt(data)

    @staticmethod
    def decrypt_session(data: bytes, key: str = "instaauto-session-key") -> bytes:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"session-salt", iterations=100000)
        fernet_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        f = Fernet(fernet_key)
        return f.decrypt(data)
