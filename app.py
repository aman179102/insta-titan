import os
import json
import time
import threading
from datetime import datetime
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from src.config_loader import load_config
from src.db.models import Database
from src.utils.helpers import logger

app = Flask(__name__)
config = load_config()
ui_config = config.get("web_ui", {})
app.secret_key = ui_config.get("secret_key", "instaauto-secret")
app.config["WTF_CSRF_ENABLED"] = False
socketio = SocketIO(app, cors_allowed_origins="*")

db_path = os.path.join(config.get("app", {}).get("data_dir", "data"), "instaauto.db")
db = Database(db_path)

# Lazy imports for heavy modules
_poster = None
_scheduler = None
_fetcher = None


def get_poster():
    global _poster
    if _poster is None:
        from src.poster.instagram import InstagramPoster
        _poster = InstagramPoster(config, db)
    return _poster


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        from src.scheduler.engine import SmartScheduler
        _scheduler = SmartScheduler(config, db, get_poster())
    return _scheduler


def get_fetcher():
    global _fetcher
    if _fetcher is None:
        from src.fetcher.orchestrator import FetcherOrchestrator
        _fetcher = FetcherOrchestrator(config, db)
    return _fetcher


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route("/")
def dashboard():
    return render_template("dashboard.html", config=config)


@app.route("/queue")
def queue_page():
    return render_template("queue.html")


@app.route("/history")
def history_page():
    return render_template("history.html")


@app.route("/config")
def config_page():
    return render_template("settings.html", config=config)


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")


@app.route("/api/stats")
def api_stats():
    try:
        from src.analytics.tracker import AnalyticsTracker
        tracker = AnalyticsTracker(config, db)
        stats = tracker.get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/queue")
def api_queue():
    status = request.args.get("status", "queued")
    queue = db.get_queue(status=status, limit=200)
    return jsonify([
        {
            "id": q.id,
            "image_path": q.image_path,
            "caption": (q.caption or "")[:80],
            "source": q.source,
            "status": q.status,
            "priority": q.priority,
            "created_at": q.created_at.isoformat() if q.created_at else "",
            "scheduled_at": q.scheduled_at.isoformat() if q.scheduled_at else "",
        }
        for q in queue
    ])


@app.route("/api/history")
def api_history():
    query = request.args.get("q", "")
    if query:
        history = db.search_history(query)
    else:
        history = db.get_session().query(db.__class__.__bases__[0].classes.get("PostedHistory", None)).order_by(
            db.__class__.__bases__[0].classes["PostedHistory"].posted_at.desc()
        ).limit(100).all() if False else []
        try:
            from src.db.models import PostedHistory
            session = db.get_session()
            history = session.query(PostedHistory).order_by(PostedHistory.posted_at.desc()).limit(100).all()
            session.close()
        except:
            history = []
    return jsonify([
        {
            "id": h.id,
            "caption": (h.caption or "")[:80],
            "source": h.source,
            "posted_at": h.posted_at.isoformat() if h.posted_at else "",
            "post_url": h.post_url or "",
            "likes": h.likes_count or 0,
            "comments": h.comments_count or 0,
        }
        for h in history
    ])


@app.route("/api/scheduler/status")
def api_scheduler_status():
    sched = get_scheduler()
    status = sched.get_status()
    return jsonify({
        "running": status["running"],
        "next_post": status["next_post"].isoformat() if status["next_post"] else None,
        "queue_count": status["queue_count"],
    })


@app.route("/api/scheduler/start", methods=["POST"])
def api_scheduler_start():
    get_scheduler().start()
    return jsonify({"status": "started"})


@app.route("/api/scheduler/stop", methods=["POST"])
def api_scheduler_stop():
    get_scheduler().stop()
    return jsonify({"status": "stopped"})


@app.route("/api/scheduler/post-now", methods=["POST"])
def api_post_now():
    success = get_scheduler().post_now()
    return jsonify({"success": success})


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    source = request.json.get("source", "all")
    if source == "all":
        count = get_fetcher().fetch_all()
    else:
        count = get_fetcher().fetch_source(source)
    return jsonify({"fetched": count})


@app.route("/api/queue/delete", methods=["POST"])
def api_queue_delete():
    post_id = request.json.get("id")
    if post_id:
        session = db.get_session()
        try:
            from src.db.models import PostQueue
            post = session.query(PostQueue).filter(PostQueue.id == post_id).first()
            if post:
                session.delete(post)
                session.commit()
                return jsonify({"success": True})
        except:
            session.rollback()
        finally:
            session.close()
    return jsonify({"success": False}), 400


@app.route("/api/queue/clear", methods=["POST"])
def api_queue_clear():
    session = db.get_session()
    try:
        from src.db.models import PostQueue
        session.query(PostQueue).filter(PostQueue.status == "queued").delete()
        session.commit()
        return jsonify({"success": True})
    except:
        session.rollback()
        return jsonify({"success": False}), 500
    finally:
        session.close()


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        import yaml
        new_config = request.json
        with open("config.yaml", "w") as f:
            yaml.dump(new_config, f)
        global config
        config = load_config()
        return jsonify({"success": True})
    return jsonify(config)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    results = db.search_queue(q) if q else []
    return jsonify([
        {
            "id": r.id,
            "caption": (r.caption or "")[:100],
            "source": r.source,
            "image_path": r.image_path,
            "status": r.status,
        }
        for r in results
    ])


@socketio.on("connect")
def handle_connect():
    emit("connected", {"status": "ok"})


def _self_pinger():
    public_url = os.environ.get("RENDER_EXTERNAL_URL") or ui_config.get("public_url", "")
    if not public_url:
        logger.warning("Self-pinger disabled: no RENDER_EXTERNAL_URL or web_ui.public_url set")
        return
    health_url = f"{public_url.rstrip('/')}/health"
    logger.info(f"Self-pinger started → pinging {health_url} every 5 min")
    while True:
        try:
            requests.get(health_url, timeout=10)
            logger.debug(f"Self-ping OK → {health_url}")
        except Exception as e:
            logger.warning(f"Self-ping failed: {e}")
        time.sleep(300)


def run_webui():
    host = ui_config.get("host", "0.0.0.0")
    port = ui_config.get("port", 5000)
    debug = ui_config.get("debug", False)
    pinger = threading.Thread(target=_self_pinger, daemon=True)
    pinger.start()
    logger.info(f"Web UI: http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_webui()
