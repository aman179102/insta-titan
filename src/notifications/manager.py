import os
import requests
from src.utils.helpers import logger


class NotificationManager:
    def __init__(self, config: dict):
        self.config = config.get("notifications", {})
        self.telegram_cfg = self.config.get("telegram", {})
        self.discord_cfg = self.config.get("discord", {})
        self.email_cfg = self.config.get("email", {})
        self.console_cfg = self.config.get("console", True)

    def send(self, message: str, level: str = "info"):
        if self.console_cfg:
            print(f"[{level.upper()}] {message}")
        if self.telegram_cfg.get("enabled"):
            self._send_telegram(message)
        if self.discord_cfg.get("enabled"):
            self._send_discord(message)
        if self.email_cfg.get("enabled"):
            self._send_email(message)

    def success(self, message: str):
        self.send(f"✅ {message}", "success")

    def error(self, message: str):
        self.send(f"❌ {message}", "error")

    def info(self, message: str):
        self.send(f"ℹ️ {message}", "info")

    def _send_telegram(self, message: str):
        try:
            token = self.telegram_cfg.get("bot_token", "")
            chat_id = self.telegram_cfg.get("chat_id", "")
            if not token or not chat_id:
                return
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")

    def _send_discord(self, message: str):
        try:
            webhook = self.discord_cfg.get("webhook_url", "")
            if not webhook:
                return
            requests.post(webhook, json={"content": message}, timeout=10)
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")

    def _send_email(self, message: str):
        try:
            import smtplib
            from email.message import EmailMessage
            cfg = self.email_cfg
            if not cfg.get("smtp_server") or not cfg.get("sender") or not cfg.get("recipients"):
                return
            msg = EmailMessage()
            msg.set_content(message)
            msg["Subject"] = "InstaAuto Notification"
            msg["From"] = cfg["sender"]
            msg["To"] = ", ".join(cfg["recipients"])
            with smtplib.SMTP(cfg["smtp_server"], cfg.get("smtp_port", 587)) as server:
                if cfg.get("password"):
                    server.starttls()
                    server.login(cfg["sender"], cfg["password"])
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
