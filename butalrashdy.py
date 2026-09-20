import asyncio
import glob
import logging
import os
import re
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlparse

import yt_dlp
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")

# ------------------------------------------------------------------
# الإعدادات
# ------------------------------------------------------------------
MAX_SIZE = 50 * 1024 * 1024  # حد تلجرام للبوتات = 50 ميجا

FORMAT = (
    "b[ext=mp4][filesize<50M]/"
    "b[ext=mp4][filesize_approx<50M]/"
    "bv*[height<=720][ext=mp4]+ba[ext=m4a]/"
    "b[ext=mp4]/b"
)

URL_REGEX = re.compile(r"https?://\S+")
SUPPORTED_DOMAINS = (
    "tiktok.com",
    "facebook.com",
    "fb.watch",
    "fb.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
)

# أقصى عدد تنزيلات في نفس الوقت (لحماية ذاكرة السيرفر المجاني)
SEM = asyncio.Semaphore(2)


# ------------------------------------------------------------------
# التحميل
# ------------------------------------------------------------------
class VideoError(Exception):
    """خطأ برسالة مناسبة لعرضها للمستخدم."""


class TooLargeError(VideoError):
    pass


def friendly_error(msg: str) -> str:
    low = msg.lower()
    if any(k in low for k in ("sign in", "log in", "login", "cookies", "not a bot", "rate-limit", "rate limit")):
        return (
            "❌ المنصة طلبت تسجيل دخول أو منعت الطلب من السيرفر.\n"
            "جرّب رابطاً آخر أو أعد المحاولة بعد قليل."
        )
    if any(k in low for k in ("private", "unavailable", "not available", "removed", "deleted")):
        return "❌ الفيديو خاص أو محذوف أو غير متاح."
    return "❌ تعذر تنزيل الفيديو. تأكد أن الرابط صحيح وأن الفيديو عام."


def download_video(url: str, out_dir: str):
    """تنزيل الفيديو. تعيد (مسار_الملف, العنوان). تعمل في thread منفصل."""
    opts = {
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "format": FORMAT,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "restrictfilenames": True,
    }
    # اختياري: بروكسي عبر متغير بيئة PROXY
    proxy = os.getenv("PROXY")
    if proxy:
        opts["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise VideoError(friendly_error(str(e))) from e

    if info and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        info = entries[0] if entries else None
    if not info:
        raise VideoError("❌ لم أجد فيديو في هذا الرابط.")

    downloads = info.get("requested_downloads") or []
    path = downloads[0].get("filepath") if downloads else None
    if not path or not os.path.exists(path):
        files = glob.glob(os.path.join(out_dir, "*"))
        if not files:
            raise VideoError("❌ لم أجد الملف بعد التنزيل.")
        path = max(files, key=os.path.getsize)

    if os.path.getsize(path) > MAX_SIZE:
        raise TooLargeError(
            "⚠️ حجم الفيديو أكبر من 50 ميجا، وتلجرام لا يسمح للبوتات بإرسال ملفات بهذا الحجم."
        )

    return path, (info.get("title") or "")


# ------------------------------------------------------------------
# البوت
# ------------------------------------------------------------------
def is_supported(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in SUPPORTED_DOMAINS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك 👋\n"
        "أرسل لي رابط فيديو من:\n"
        "• تيك توك\n• فيسبوك\n• يوتيوب\n• انستجرام\n\n"
        "وسأرسل لك الفيديو مباشرة 🎬"
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    match = URL_REGEX.search(msg.text)
    if not match:
        await msg.reply_text("أرسل رابط فيديو صحيح من فضلك 🔗")
        return

    url = match.group(0)
    if not is_supported(url):
        await msg.reply_text(
            "❌ هذا الرابط غير مدعوم.\n"
            "المنصات المدعومة: تيك توك، فيسبوك، يوتيوب، انستجرام."
        )
        return

    status = await msg.reply_text("⏳ جاري التنزيل، انتظر قليلاً...")

    async with SEM:
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                await msg.chat.send_action(ChatAction.UPLOAD_VIDEO)
                path, title = await asyncio.to_thread(download_video, url, tmp_dir)
            except VideoError as e:
                await status.edit_text(str(e))
                return
            except Exception:
                logger.exception("Unexpected download error")
                await status.edit_text("❌ حدث خطأ غير متوقع أثناء التنزيل.")
                return

            try:
                await status.edit_text("📤 جاري الإرسال...")
                with open(path, "rb") as f:
                    await msg.reply_video(
                        video=f,
                        caption=title[:1000],
                        supports_streaming=True,
                        read_timeout=180,
                        write_timeout=180,
                        connect_timeout=60,
                    )
                await status.delete()
            except TelegramError:
                logger.exception("Send failed")
                await status.edit_text("❌ حدث خطأ أثناء إرسال الفيديو.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error", exc_info=context.error)


def build_app(token: str):
    app = ApplicationBuilder().token(token).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_error_handler(on_error)
    return app


# ------------------------------------------------------------------
# سيرفر Flask (للإبقاء على الخدمة مستيقظة على Render)
# ------------------------------------------------------------------
web = Flask(__name__)


@web.route("/")
def home():
    return "Bot is running ✅"


@web.route("/health")
def health():
    return "OK", 200


def run_server():
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    port = int(os.getenv("PORT", "10000"))
    web.run(host="0.0.0.0", port=port, use_reloader=False)


def self_ping():
    """يرسل طلباً لنفسه كل 10 دقائق (Render يوفر RENDER_EXTERNAL_URL تلقائياً)."""
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(url + "/health", timeout=15).read()
        except Exception as e:
            logger.warning("Self ping failed: %s", e)


# ------------------------------------------------------------------
# التشغيل
# ------------------------------------------------------------------
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN غير موجود. أضفه في Environment على Render.")

    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

   logger.info("Bot is starting...")
    asyncio.set_event_loop(asyncio.new_event_loop())
    build_app(token).run_polling(drop_pending_updates=True) 


if __name__ == "__main__":
    main()
