#!/usr/bin/env python3
"""
InstaAuto — Ultimate Instagram Automation Platform
NASA/ISRO/Google/Microsoft engineers ko paseena nikalane wala project 🚀
"""

import os
import sys
import time
import threading
import argparse
from datetime import datetime
import requests
from src.config_loader import load_config
from src.db.models import Database
from src.utils.helpers import logger, ensure_dir


def main():
    parser = argparse.ArgumentParser(
        description="InstaAuto — Instagram Automation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run              Start scheduler
  python main.py web              Start web UI
  python main.py fetch            Fetch images from all sources
  python main.py queue            Show queued posts
  python main.py post-now         Post one immediately
  python main.py search "nature"  Search queue/history
  python main.py config           Show config
  python main.py telegram         Start Telegram bot
        """
    )

    parser.add_argument("command", nargs="?", default="run",
                        help="Command: run, web, fetch, queue, post-now, search, config, telegram")
    parser.add_argument("query", nargs="?", default="", help="Search query or other argument")
    parser.add_argument("--config", "-c", default="config.yaml", help="Config file path")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Web UI port")

    args = parser.parse_args()

    config = load_config(args.config)
    ensure_dir(config.get("app", {}).get("data_dir", "data"))

    db_path = os.path.join(config.get("app", {}).get("data_dir", "data"), "instaauto.db")
    db = Database(db_path)

    from src.fetcher.orchestrator import FetcherOrchestrator
    fetcher = FetcherOrchestrator(config, db)

    from src.poster.instagram import InstagramPoster
    poster = InstagramPoster(config, db)

    from src.scheduler.engine import SmartScheduler
    scheduler = SmartScheduler(config, db, poster)

    from src.filter.content import FilterPipeline
    filter_pipeline = FilterPipeline(config, db)

    from src.notifications.manager import NotificationManager
    notifier = NotificationManager(config)

    cmd = args.command

    if cmd == "run":
        logger.info("=" * 50)
        logger.info("🚀 InstaAuto Starting...")
        logger.info("=" * 50)

        scheduler.start()

        pinger_thread = threading.Thread(target=_self_pinger, args=(config,), daemon=True)
        pinger_thread.start()

        status_thread = threading.Thread(target=_status_logger, args=(db,), daemon=True)
        status_thread.start()

        health_thread = threading.Thread(target=_health_server, args=(config, db), daemon=True)
        health_thread.start()

        logger.info("🤖 Telegram Bot starting (main thread)...")
        _start_telegram(config, db, fetcher, poster, scheduler)

    elif cmd == "web":
        web_config = config.get("web_ui", {})
        os.environ["FLASK_PORT"] = str(args.port or web_config.get("port", 5000))
        from app import run_webui
        run_webui()

    elif cmd == "fetch":
        source = args.query if args.query else "all"
        if source == "all":
            count = fetcher.fetch_all()
        else:
            count = fetcher.fetch_source(source)
        print(f"✅ Fetched {count} images from '{source}'")
        if db.queue_count() > 0:
            print(f"📦 Queue now has {db.queue_count()} items")

    elif cmd == "queue":
        queue = db.get_queue(limit=50)
        if not queue:
            print("📭 Queue is empty. Use 'fetch' to get images.")
            return
        print(f"\n{'='*60}")
        print(f"📦 Post Queue ({len(queue)} items)")
        print(f"{'='*60}")
        for i, q in enumerate(queue[:20], 1):
            status_icon = "⏳" if q.status == "queued" else "✅" if q.status == "posted" else "❌"
            caption = (q.caption or "")[:50]
            print(f" {i:2d}. {status_icon} [{q.source:12s}] {caption}")

    elif cmd == "post-now":
        print("📤 Posting now...")
        success, reason = scheduler.post_now()
        if success:
            print("✅ Posted!")
        else:
            print(f"❌ Failed: {reason or 'Unknown error'}")

    elif cmd == "search":
        q = args.query
        if not q:
            print("❌ Please provide a search query")
            return
        print(f"\n🔍 Searching for '{q}'...")
        queue_results = db.search_queue(q)
        hist_results = db.search_history(q)
        print(f"\n📦 Queue matches: {len(queue_results)}")
        for r in queue_results[:5]:
            print(f"   • [{r.source}] {(r.caption or '')[:60]}")
        print(f"\n📜 History matches: {len(hist_results)}")
        for r in hist_results[:5]:
            print(f"   • [{r.source}] {(r.caption or '')[:60]}")

    elif cmd == "config":
        import yaml
        print(yaml.dump(config, default_flow_style=False))

    elif cmd == "telegram":
        from src.notifications.telegram_bot import TelegramBot
        bot = TelegramBot(config, db, fetcher, poster, scheduler)
        poster.notify_callback = bot.send_alert
        print("🤖 Telegram Bot starting...")
        bot.run()

    elif cmd == "health":
        accounts = config.get("instagram", {}).get("accounts", [])
        for acc in accounts:
            if acc.get("enabled") and acc.get("username"):
                score = poster.check_health(acc["username"])
                print(f"📊 {acc['username']}: Health Score = {score:.1f}%")

    elif cmd == "analytics":
        from src.analytics.tracker import AnalyticsTracker
        tracker = AnalyticsTracker(config, db)
        stats = tracker.get_dashboard_stats()
        print("\n📊 Dashboard Stats")
        print(f"{'='*40}")
        print(f"  In Queue:     {stats.get('total_queued', 0)}")
        print(f"  Posted Today: {stats.get('posted_today', 0)}")
        print(f"  Total Posted: {stats.get('total_posted', 0)}")
        print(f"  Failed:       {stats.get('failed', 0)}")
        print(f"  This Week:    {stats.get('posted_week', 0)}")

    elif cmd == "vault":
        from src.security.vault import CredentialVault
        vault = CredentialVault()
        services = vault.list_services()
        print("\n🔐 Credential Vault")
        print(f"{'='*40}")
        if services:
            for s in services:
                print(f"  • {s}")
        else:
            print("  No credentials stored")

    else:
        parser.print_help()


def _health_server(config, db):
    import http.server
    import json as json_mod
    port = int(os.environ.get("PORT") or config.get("web_ui", {}).get("port", 5000))

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                data = json_mod.dumps({"status": "ok", "timestamp": time.time()})
            elif self.path == "/status":
                q = db.queue_count() if db else 0
                data = json_mod.dumps({"status": "ok", "queue_count": q})
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data.encode())

        def log_message(self, format, *args):
            pass

    try:
        server = http.server.HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"Health server: http://0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed: {e}")


def _status_logger(db):
    while True:
        time.sleep(60)
        queue_count = db.queue_count()
        posted_today = db.posts_posted_today()
        logger.info(f"Status: {queue_count} queued | {posted_today} posted today")


def _start_telegram(config, db, fetcher, poster, scheduler):
    from src.notifications.telegram_bot import TelegramBot
    bot = TelegramBot(config, db, fetcher, poster, scheduler)
    poster.notify_callback = bot.send_alert
    logger.info("🤖 Telegram Bot starting...")
    bot.run()


def _self_pinger(config):
    from src.db.models import Database
    db_path = os.path.join(config.get("app", {}).get("data_dir", "data"), "instaauto.db")
    pinger_db = Database(db_path)
    public_url = os.environ.get("RENDER_EXTERNAL_URL") or config.get("web_ui", {}).get("public_url", "")
    if not public_url:
        logger.warning("Self-pinger disabled: no RENDER_EXTERNAL_URL or web_ui.public_url set")
        return
    health_url = f"{public_url.rstrip('/')}/health"
    logger.info(f"Self-pinger started → pinging {health_url} every 5 min")
    consecutive_failures = 0
    while True:
        try:
            start = time.time()
            requests.get(health_url, timeout=10)
            elapsed = int((time.time() - start) * 1000)
            pinger_db.log_ping(status="ok", duration_ms=elapsed)
            consecutive_failures = 0
            logger.debug(f"Self-ping OK → {health_url} ({elapsed}ms)")
        except Exception as e:
            try:
                pinger_db.log_ping(status="failed", error_message=str(e))
            except Exception:
                pass
            consecutive_failures += 1
            logger.warning(f"Self-ping failed ({consecutive_failures}x): {e}")
        finally:
            time.sleep(300)


if __name__ == "__main__":
    main()
