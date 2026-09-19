import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# 1. إعداد سيرفر ويب وهمي لجعل Render يترك البوت يعمل 24 ساعة
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
TOKEN = "8948025390:AAFMgibR1kMcRohobi65uSuqJoA2NV4Tqyo"

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
    
    processing_msg = await update.message.reply_text("⚡ جاري تحميل وإرسال الفيديو، انتظر قليلاً...")

    output_filename = f"video_{chat_id}.mp4"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 30,
    }

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await loop.run_in_executor(None, download)

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
                            caption="✅ تم التحميل وإرسال الفيديو بنجاح!"
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
            await processing_msg.edit_text("❌ لم أتمكن من استخراج الفيديو. تأكد أن الرابط صالح.")

    except Exception as e:
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحميل أو الاتصال. تأكد أن الرابط عام وليس محمياً بحساب خاص.")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    # تشغيل سيرفر الويب الوهمي أولاً لمنع إغلاق ريندر
    keep_alive()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running smoothly and ready...")
    app.run_polling()

if __name__ == "__main__":
    main()
