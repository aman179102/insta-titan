import os
import time
import io
import logging
from datetime import datetime
from src.utils.helpers import logger


class TelegramBot:
    def __init__(self, config: dict, db=None, fetcher=None, poster=None, scheduler=None):
        self.config = config
        self.db = db
        self.fetcher = fetcher
        self.poster = poster
        self.scheduler = scheduler
        self.bot_token = config.get("notifications", {}).get("telegram", {}).get("bot_token", "")
        self.chat_id = config.get("notifications", {}).get("telegram", {}).get("chat_id", "")

    def run(self):
        try:
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

            if not self.bot_token:
                logger.error("Telegram: No bot token configured")
                return

            app = Application.builder().token(self.bot_token).build()

            app.add_handler(CommandHandler("start", self.cmd_start))
            app.add_handler(CommandHandler("stats", self.cmd_stats))
            app.add_handler(CommandHandler("queue", self.cmd_queue))
            app.add_handler(CommandHandler("fetch", self.cmd_fetch))
            app.add_handler(CommandHandler("post", self.cmd_post))
            app.add_handler(CommandHandler("ping", self.cmd_ping))
            app.add_handler(CommandHandler("health", self.cmd_health))
            app.add_handler(CommandHandler("sources", self.cmd_sources))
            app.add_handler(CommandHandler("help", self.cmd_help))

            logger.info("Telegram Bot started! Commands: /stats /queue /fetch /post /ping /health /sources /help")
            app.run_polling(allowed_updates=Update.ALL_TYPES)

        except ImportError:
            logger.warning("Telegram: python-telegram-bot not installed")

    async def cmd_start(self, update, context):
        await update.message.reply_text(
            "🤖 *InstaAuto Bot — Production Ready*\n\n"
            "Ab aap Telegram se hi sab kuch control kar sakte ho.\n\n"
            "*Commands:*\n"
            "/stats  — 📊 Queue, posted, sources summary\n"
            "/queue  — 📦 View queued posts\n"
            "/fetch  — 🔄 Fetch images from all sources\n"
            "/post   — 📤 Post one now\n"
            "/ping   — 📡 Check ping monitor status\n"
            "/health — ❤️ Instagram account health\n"
            "/sources — 🌐 Source-wise stats\n"
            "/help   — ℹ️ This message",
            parse_mode="Markdown"
        )

    async def cmd_stats(self, update, context):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        try:
            queue_count = self.db.queue_count()
            posted_today = self.db.posts_posted_today()
            from src.db.models import PostedHistory, PingLog, Source
            session = self.db.get_session()
            total_posted = session.query(PostedHistory).count()
            failed = session.query(PostedHistory.__class__).filter(PostedHistory.__class__.__name__ == "PostQueue").count() if False else 0
            session.close()
            try:
                session2 = self.db.get_session()
                from src.db.models import PostQueue
                failed = session2.query(PostQueue).filter(PostQueue.status == "failed").count()
                session2.close()
            except:
                failed = 0

            last_ping = self.db.get_last_ping()
            ping_status = "✅ Active" if last_ping and last_ping.status == "ok" else "⏳ Waiting" if not last_ping else "❌ Failing"

            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M")

            msg = (
                f"📊 *InstaAuto Status*\n"
                f"🕐 {now}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📦 Queue:      {queue_count}\n"
                f"📤 Today:      {posted_today}\n"
                f"📈 Total:      {total_posted}\n"
                f"❌ Failed:     {failed}\n"
                f"📡 Ping:       {ping_status}\n"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_queue(self, update, context):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        try:
            queue = self.db.get_queue(limit=10)
            if not queue:
                await update.message.reply_text("📭 Queue is empty.\nUse /fetch to get images first.")
                return
            msg = f"📦 *Queue* (top {len(queue)}):\n\n"
            for i, q in enumerate(queue, 1):
                caption = (q.caption or "Untitled")[:40]
                msg += f"{i}. [{q.source}] {caption}\n"
            msg += f"\nUse /post to post one now."
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_fetch(self, update, context):
        if not self.fetcher:
            await update.message.reply_text("❌ Fetcher not available")
            return
        await update.message.reply_text("🔄 Fetching images from all sources...")
        try:
            count = self.fetcher.fetch_all()
            q = self.db.queue_count() if self.db else 0
            await update.message.reply_text(f"✅ Fetched {count} images!\n📦 Queue now has {q} items.")
        except Exception as e:
            await update.message.reply_text(f"❌ Fetch failed: {e}")

    async def cmd_post(self, update, context):
        if not self.scheduler:
            await update.message.reply_text("❌ Scheduler not available")
            return
        if self.db:
            q = self.db.queue_count()
            if q == 0:
                await update.message.reply_text("📭 No images in queue. Use /fetch first!")
                return
        await update.message.reply_text("📤 Posting now...")
        success = self.scheduler.post_now()
        if success:
            await update.message.reply_text("✅ Posted successfully to Instagram!")
        else:
            await update.message.reply_text("❌ Failed to post. Check logs or use /queue to see available posts.")

    async def cmd_ping(self, update, context):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        try:
            last_ping = self.db.get_last_ping()
            if not last_ping:
                await update.message.reply_text("📡 No pings recorded yet.\nWait 5 min for first ping.")
                return
            ago = ""
            if last_ping.created_at:
                diff = int((datetime.now() - last_ping.created_at).total_seconds())
                if diff < 60:
                    ago = f"{diff}s ago"
                elif diff < 3600:
                    ago = f"{diff // 60}m ago"
                else:
                    ago = f"{diff // 3600}h ago"
            if last_ping.status == "ok":
                await update.message.reply_text(
                    f"📡 *Ping Monitor*\n\n"
                    f"✅ Status: Active\n"
                    f"🕐 Last: {ago}\n"
                    f"⚡ Response: {last_ping.response_time_ms}ms",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"📡 *Ping Monitor*\n\n"
                    f"❌ Status: Failing\n"
                    f"🕐 Last: {ago}\n"
                    f"⚠️ Error: {last_ping.error_message or 'Unknown'}",
                    parse_mode="Markdown"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_health(self, update, context):
        if not self.poster:
            await update.message.reply_text("❌ Poster not available")
            return
        accounts = self.config.get("instagram", {}).get("accounts", [])
        if not accounts:
            await update.message.reply_text("❌ No Instagram accounts configured")
            return
        msg = "❤️ *Account Health*\n\n"
        for acc in accounts:
            if acc.get("enabled") and acc.get("username"):
                try:
                    score = self.poster.check_health(acc["username"])
                    icon = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
                    msg += f"{icon} {acc['username']}: {score:.0f}%\n"
                except Exception as e:
                    msg += f"❌ {acc['username']}: {e}\n"
        msg += "\nUse /stats for general stats."
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_sources(self, update, context):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        try:
            from src.db.models import Source
            session = self.db.get_session()
            sources = session.query(Source).all()
            session.close()
            if not sources:
                sources_cfg = self.config.get("sources", {})
                enabled = [k for k, v in sources_cfg.items() if isinstance(v, dict) and v.get("enabled")]
                if enabled:
                    await update.message.reply_text(
                        f"🌐 *Enabled Sources*\n\n" + "\n".join(f"✅ {s}" for s in enabled) +
                        "\n\nNo fetch data yet. Use /fetch to get images.",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text("❌ No sources enabled in config.")
                return
            msg = "🌐 *Sources*\n\n"
            for s in sources:
                msg += f"✅ {s.name}: {s.total_fetched or 0} fetched, {s.total_posted or 0} posted\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_help(self, update, context):
        await update.message.reply_text(
            "🤖 *InstaAuto Bot*\n\n"
            "*Commands:*\n"
            "/start  — Welcome & intro\n"
            "/stats  — Queue, posted, ping status\n"
            "/queue  — Show queued posts (top 10)\n"
            "/fetch  — Fetch images from all sources\n"
            "/post   — Post one queued image now\n"
            "/ping   — Live ping monitor status\n"
            "/health — Instagram account health check\n"
            "/sources — Source-wise fetch/post stats\n"
            "/help   — This message\n\n"
            "⚡ Auto-ping har 5 min chal raha hai — server sleep nahi hoga.",
            parse_mode="Markdown"
        )