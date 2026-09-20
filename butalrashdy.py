# -*- coding: utf-8 -*-
import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# 1. إعداد سيرفر ويب للحفاظ على ديمومة عمل البوت 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Facebook Bot is active and running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# التوكن الخاص بالبوت
TOKEN = "8956631728:AAE_gm59PZECONsyUyhm4b8GqKbcGId10QE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في بوت تحميل فيديوهات فيسبوك فقط! 📘🔥\n\n"
        "أرسل أي رابط فيديو أو ريلز (Reels) من فيسبوك وسأقوم بتحميله وإرساله إليك فوراً وبأفضل جودة!"
    )

async def download_facebook_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if "facebook.com" not in url and "fb.watch" not in url:
        await update.message.reply_text("❌ هذا البوت مخصص لفيسبوك فقط. الرجاء إرسال رابط فيسبوك صالح.")
        return

    processing_msg = await update.message.reply_text("⏳ جاري سحب ومعالجة فيديو الفيسبوك، انتظر قليلاً...")

    output_filename = f"fb_video_{chat_id}.mp4"

    # إعدادات مخصصة ومستقرة لروابط الفيسبوك
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'socket_timeout': 60,
        'retries': 20,
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
                            caption="✅ تم إرسال فيديو الفيسبوك بنجاح بواسطة بوت الراشدي!"
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
            await processing_msg.edit_text("❌ لم أتمكن من سحب الفيديو. تأكد أن المنشور عام وليس خاصاً.")

    except Exception as e:
        await processing_msg.edit_text("❌ حدث خطأ أثناء الاتصال برابط الفيسبوك. تأكد أن الرابط صحيح وعام.")
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_facebook_video))

    print("Facebook Bot is running and ready...")
    app.run_polling()

if __name__ == "__main__":
    main()
