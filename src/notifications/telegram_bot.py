import os
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
            app.add_handler(CommandHandler("help", self.cmd_help))

            logger.info("Telegram Bot started! Send /start to your bot.")
            app.run_polling(allowed_updates=Update.ALL_TYPES)

        except ImportError:
            logger.warning("Telegram: python-telegram-bot not installed")
            logger.info("Install: pip install python-telegram-bot")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *InstaAuto Bot*\n\n"
            "Your Instagram automation control center.\n\n"
            "Commands:\n"
            "/stats  — Show dashboard stats\n"
            "/queue  — Show queued posts\n"
            "/fetch  — Fetch new images\n"
            "/post   — Post one now\n"
            "/help   — This message",
            parse_mode="Markdown"
        )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        queue_count = self.db.queue_count()
        posted_today = self.db.posts_posted_today()
        total_posted = self.db.get_session().query(self.db.__class__.__bases__[0].classes.get("PostedHistory", None)).count() if False else 0
        try:
            from src.db.models import PostedHistory
            session = self.db.get_session()
            total_posted = session.query(PostedHistory).count()
            session.close()
        except:
            total_posted = 0

        msg = (
            f"📊 *InstaAuto Stats*\n"
            f"📦 Queue: {queue_count}\n"
            f"📤 Posted Today: {posted_today}\n"
            f"📈 Total Posted: {total_posted}\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.db:
            await update.message.reply_text("❌ Database not available")
            return
        queue = self.db.get_queue(limit=10)
        if not queue:
            await update.message.reply_text("📭 Queue is empty")
            return
        msg = "📦 *Queue* (top 10):\n\n"
        for i, q in enumerate(queue, 1):
            caption = (q.caption or "")[:40]
            msg += f"{i}. [{q.source}] {caption}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_fetch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.fetcher:
            await update.message.reply_text("❌ Fetcher not available")
            return
        await update.message.reply_text("🔄 Fetching images...")
        try:
            count = self.fetcher.fetch_all()
            await update.message.reply_text(f"✅ Fetched {count} images!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.scheduler:
            await update.message.reply_text("❌ Scheduler not available")
            return
        await update.message.reply_text("📤 Posting now...")
        success = self.scheduler.post_now()
        if success:
            await update.message.reply_text("✅ Posted!")
        else:
            await update.message.reply_text("❌ Failed to post")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *InstaAuto Bot Commands*\n\n"
            "/start — Welcome message\n"
            "/stats — Dashboard statistics\n"
            "/queue — Show queued posts\n"
            "/fetch — Fetch new images from all sources\n"
            "/post  — Post one queued image now\n"
            "/help  — This help message",
            parse_mode="Markdown"
        )
