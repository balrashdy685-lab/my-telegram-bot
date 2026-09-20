# -*- coding: utf-8 -*-
import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# 1. إعداد سيرفر ويب وهمي للحفاظ على ديمومة عمل البوت 24/7
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
        "أهلاً بك في بوت التحميل الشامل المطور (نسخة الموبايل الخارقة) 🚀🔥\n\n"
        "جاهز لتحميل الفيديوهات بكفاءة عالية من:\n"
        "🔹 يوتيوب (بواسطة محاكي تطبيقات الأندرويد)\n"
        "🔹 فيسبوك (Facebook)\n"
        "🔹 تيك توك (TikTok)\n"
        "🔹 انستجرام (Instagram)\n\n"
        "فقط أرسل رابط الفيديو وسأتولى التحميل فوراً!"
    )

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if not url.startswith("http"):
        await update.message.reply_text("❌ الرجاء إرسال رابط صالح يبدأ بـ http أو https.")
        return

    processing_msg = await update.message.reply_text("⏳ جاري سحب ومعالجة الرابط عبر مشغل التطبيقات الذكي، انتظر قليلاً...")

    output_filename = f"video_{chat_id}.mp4"

    # إعدادات ذكية جداً تخدع حماية يوتيوب وفيسبوك عبر محاكاة عميل أندرويد
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 60,
        'retries': 30,
        'geo_bypass': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # الحل العبقري: خداع يوتيوب بالظهور كتطبيق هاتف محمول لتفادي حظر السيرفرات
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        }
    }

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await loop.run_in_executor(None, download)

        if os.path.exists(output_filename):
            file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
            await processing_msg.edit_text(f"📤 تم التحميل بنجاح (الحجم: {file_size_mb:.1f} MB)، جاري الرفع...")
            
            await update.message.reply_chat_action("upload_video")
            
            for attempt in range(3):
                try:
                    with open(output_filename, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=chat_id, 
                            video=video_file,
                            supports_streaming=True,
                            caption="✅ تم إرسال الفيديو بنجاح بواسطة بوت الراشدي الخارق!"
                        )
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    await asyncio.sleep(3)

            if os.path.exists(output_filename):
                os.remove(output_filename)
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ لم استطع سحب هذا الرابط. تأكد أنه عام وليس خاصاً.")

    except Exception as e:
        await processing_msg.edit_text("❌ حدث خطأ أثناء الاتصال بالرابط. يوتيوب أو فيسبوك قد يفرضان قيوداً على هذا الرابط المحدد.")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running and ready with Android spoofing...")
    app.run_polling()

if __name__ == "__main__":
    main()
