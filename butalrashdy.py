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
        "أهلاً بك في بوت التحميل الشامل الخارق! 🚀🔥\n\n"
        "جاهز لتحميل أي فيديو (حتى لو كان حجمه 1 جيجا أو أكثر) من:\n"
        "🔹 يوتيوب (YouTube)\n"
        "🔹 فيسبوك (Facebook)\n"
        "🔹 تيك توك (TikTok - بدون علامة مائية)\n"
        "🔹 انستجرام (Instagram - Reels & Videos)\n\n"
        "فقط أرسل الرابط وسأتولى التحميل مهما كان حجمه!"
    )

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if not url.startswith("http"):
        await update.message.reply_text("❌ الرجاء إرسال رابط صالح يبدأ بـ http أو https.")
        return

    processing_msg = await update.message.reply_text("⏳ جاري سحب وتنزيل الفيديو (قد يستغرق الملف الكبير وقتاً أطول، انتظر قليلاً)...")

    output_filename = f"video_{chat_id}.mp4"

    # إعدادات فائقة القوة للتعامل مع الملفات الضخمة والروابط المعقدة لكافة المنصات
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # صيغة مدمجة ومستقرة تتجنب أخطاء الدمج وتدعم الحجم الكبير
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 60,          # زيادة مهلة الانتظار للملفات الضخمة
        'retries': 20,                 # محاولات متكررة عند ضعف الاتصال
        'fragment_retries': 20,
        'geo_bypass': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        # تنفيذ التحميل في مسار منفصل لكي لا يتجمد البوت
        await loop.run_in_executor(None, download)

        if os.path.exists(output_filename):
            file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
            await processing_msg.edit_text(f"📤 تم التحميل بنجاح (الحجم: {file_size_mb:.1f} MB)، جاري رفع الفيديو إليك...")
            
            await update.message.reply_chat_action("upload_video")
            
            # محاولات متعددة لرفع الملفات الكبيرة لتجاوز ضغط الشبكة
            success = False
            for attempt in range(3):
                try:
                    with open(output_filename, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=chat_id, 
                            video=video_file,
                            supports_streaming=True,
                            caption="✅ تم رفع الفيديو بنجاح بواسطة بوت الراشدي الخارق!"
                        )
                    success = True
                    break
                except Exception as upload_err:
                    if attempt == 2:
                        raise upload_err
                    await asyncio.sleep(5)

            # تنظيف السيرفر وحذف الملف بعد الإرسال لتفريغ الذاكرة
            if os.path.exists(output_filename):
                os.remove(output_filename)
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ لم أتمكن من استخراج الفيديو. تأكد أن الرابط عام وليس محمياً بحساب خاص.")

    except Exception as e:
        await processing_msg.edit_text(f"❌ حدث خطأ أثناء التحميل أو الاتصال (الملف قد يكون محمي أو كبير جداً على السيرفر).")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    keep_alive()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running smoothly and ready for massive downloads...")
    app.run_polling()

if __name__ == "__main__":
    main()
