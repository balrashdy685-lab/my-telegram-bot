# -*- coding: utf-8 -*-
import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# 1. سيرفر الويب للحفاظ على ديمومة البوت 24/7
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# التوكن الخاص بك
TOKEN = "8956631728:AAE_gm59PZECONsyUyhm4b8GqKbcGId10QE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك يا بطل! 🚀🔥\n\n"
        "تمت استعادة استقرار تيك توك بالكامل، ودعم يوتيوب وفيسبوك عبر ملف الكوكيز الخاص بك.\n"
        "أرسل أي رابط وسأقوم بتحميله فوراً!"
    )

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if not url.startswith("http"):
        await update.message.reply_text("❌ الرجاء إرسال رابط صالح يبدأ بـ http أو https.")
        return

    processing_msg = await update.message.reply_text("⚡ جاري التحميل، انتظر قليلاً...")

    output_filename = f"video_{chat_id}.mp4"

    # التحقق مما إذا كنت قد رفعت ملف cookies.txt إلى المستودع لربطه تلقائياً
    cookie_file = "cookies.txt"
    has_cookies = os.paths.exists(cookie_file) if hasattr(os.path, 'exists') else os.path.exists(cookie_file)

    # إعدادات دقيقة تجمع بين قوة التيك توك واستقرار البقية عبر الكوكيز إن توفرت
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 60,
        'retries': 20,
        'geo_bypass': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }

    # إذا وجدنا ملف الكوكيز مرفوعاً، نقوم بتفعيله لتجاوز حظر يوتيوب وفيسبوك تماماً
    if has_cookies:
        ydl_opts['cookiefile'] = cookie_file

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await loop.run_in_executor(None, download)

        if os.path.exists(output_filename):
            await update.message.reply_chat_action("upload_video")
            
            for attempt in range(3):
                try:
                    with open(output_filename, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=chat_id, 
                            video=video_file,
                            supports_streaming=True,
                            caption="✅ تم التحميل وإرسال الفيديو بنجاح!"
                        )
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    await asyncio.sleep(2)

            if os.path.exists(output_filename):
                os.remove(output_filename)
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ لم أتمكن من استخراج الفيديو. تأكد أن الرابط صالح وعام.")

    except Exception as e:
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحميل. تأكد أن الرابط ليس محمياً أو خاصاً.")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    keep_alive()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == "__main__":
    main()
