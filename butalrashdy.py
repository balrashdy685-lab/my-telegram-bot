# -*- coding: utf-8 -*-
import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# 1. إعداد سيرفر ويب وهمي لجعل Render يترك البوت يعمل 24 ساعة دون إغلاق
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# التوكن الجديد والنظيف الخاص بك
TOKEN = "8956631728:AAE_gm59PZECONsyUyhm4b8GqKbcGId10QE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في بوت التحميل الشامل! 🚀🔥\n\n"
        "أنا جاهز لتحميل الفيديوهات من:\n"
        "🔹 فيسبوك (Facebook)\n"
        "🔹 تيك توك (TikTok)\n"
        "🔹 يوتيوب (YouTube)\n"
        "🔹 انستجرام (Instagram)\n\n"
        "فقط أرسل رابط الفيديو وسأتولى الباقي فوراً!"
    )

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if not url.startswith("http"):
        await update.message.reply_text("❌ الرجاء إرسال رابط صالح يبدأ بـ http أو https.")
        return

    processing_msg = await update.message.reply_text("⚡ جاري تحليل وتحميل الفيديو بكل صيغه، انتظر قليلاً...")

    output_filename = f"video_{chat_id}.mp4"

    # إعدادات متقدمة ومرنة لـ yt-dlp لتجاوز حماية تيك توك، إنستغرام، وفيسبوك
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 30,
        'geo_bypass': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await loop.run_in_executor(None, download)

        # استراتيجية السقوط الآمن إذا لم يتوفر ملف الدمج
        if not os.path.exists(output_filename):
            fallback_opts = {
                'format': 'best',
                'outtmpl': output_filename,
                'noplaylist': True,
                'geo_bypass': True,
            }
            def download_fallback():
                with yt_dlp.YoutubeDL(fallback_opts) as ydl_fb:
                    ydl_fb.download([url])
            await loop.run_in_executor(None, download_fallback)

        if os.path.exists(output_filename):
            await update.message.reply_chat_action("upload_video")
            
            success = False
            for attempt in range(3):
                try:
                    with open(output_filename, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=chat_id, 
                            video=video_file,
                            supports_streaming=True,
                            caption="✅ تم التحميل وإرسال الفيديو بنجاح بواسطة بوت الراشدي!"
                        )
                    success = True
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2)

            if os.path.exists(output_filename):
                os.remove(output_filename)
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ لم أتمكن من استخراج الفيديو. تأكد أن الرابط عام وليس محمياً بحساب خاص.")

    except Exception as e:
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحميل أو الاتصال. تأكد أن الرابط عام وليس محمياً بحساب خاص.")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    # تشغيل سيرفر الويب الوهمي للحفاظ على ديمومة العمل على Render
    keep_alive()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running smoothly and ready...")
    app.run_polling()

if __name__ == "__main__":
    main()
