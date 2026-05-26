import json
import os
import uuid
import requests
import multiprocessing
import traceback
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template_string, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Load .env file
load_dotenv()

# ========== CONFIGURATION FROM ENV ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003582640643")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@cloudxstorevidf")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")
if not DOMAIN:
    raise ValueError("❌ DOMAIN not set!")

print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")
print(f"✅ Domain: {DOMAIN}")
print(f"✅ Channel: {CHANNEL_USERNAME} ({CHANNEL_ID})")

# ========== DATABASE ==========
DB_FILE = "videos_db.json"

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 Database loaded: {len(data)} videos")
                return data
    except:
        pass
    return {}

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Database saved: {len(data)} videos")
    except Exception as e:
        print(f"❌ Database save error: {e}")

# ========== FLASK APP ==========
app = Flask(__name__)

PLAYER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ file_name }}</title>
    <meta property="og:title" content="{{ file_name }}">
    <meta property="og:type" content="video.other">
    <meta property="og:video:url" content="{{ video_url }}">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 15px;
        }
        .container {
            width: 100%;
            max-width: 900px;
            background: #111;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 25px 80px rgba(0,136,204,0.15);
        }
        .video-section { background: #000; position: relative; }
        video {
            width: 100%;
            display: block;
            max-height: 75vh;
            outline: none;
        }
        .content { padding: 25px; }
        .file-name {
            color: #fff;
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 8px;
            word-break: break-word;
            line-height: 1.3;
        }
        .file-meta {
            color: #999;
            font-size: 14px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .button-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s;
            letter-spacing: 0.3px;
        }
        .btn-download {
            background: linear-gradient(135deg, #0088cc, #006699);
            color: white;
            flex: 1;
            justify-content: center;
            min-width: 160px;
        }
        .btn-download:hover {
            background: linear-gradient(135deg, #0099dd, #0077aa);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,136,204,0.4);
        }
        .btn-copy {
            background: #2a2a2a;
            color: white;
            min-width: 160px;
            justify-content: center;
        }
        .btn-copy:hover {
            background: #3a3a3a;
            transform: translateY(-2px);
        }
        .btn-copy.copied {
            background: #28a745 !important;
        }
        .link-box {
            background: #1a1a1a;
            border: 1px solid #333;
            color: #aaa;
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 14px;
            width: 100%;
            margin-top: 12px;
            word-break: break-all;
            font-family: 'Courier New', monospace;
        }
        .watermark {
            text-align: center;
            padding: 15px;
            color: #444;
            font-size: 12px;
        }
        @media (max-width: 600px) {
            .content { padding: 15px; }
            .file-name { font-size: 17px; }
            .btn { padding: 12px 20px; font-size: 14px; }
            .button-group { flex-direction: column; }
            .file-meta { flex-direction: column; gap: 5px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="video-section">
            <video controls autoplay playsinline>
                <source src="{{ video_url }}" type="video/mp4">
                Your browser does not support video playback.
            </video>
        </div>
        <div class="content">
            <div class="file-name">📹 {{ file_name }}</div>
            <div class="file-meta">
                <span>📦 {{ file_size }}</span>
                <span>📅 {{ upload_date }}</span>
                <span>👁️ {{ views }} views</span>
            </div>
            <div class="button-group">
                <a href="{{ video_url }}" download="{{ file_name }}" class="btn btn-download">
                    ⬇️ Download Video
                </a>
                <button onclick="copyLink()" class="btn btn-copy" id="copyBtn">
                    📋 Copy Link
                </button>
            </div>
            <input type="text" class="link-box" id="shareInput" 
                   value="{{ share_url }}" readonly onclick="this.select()">
        </div>
        <div class="watermark">🚀 Powered by Cloud Store • No App Needed</div>
    </div>

    <script>
        function copyLink() {
            var input = document.getElementById("shareInput");
            input.select();
            input.setSelectionRange(0, 99999);
            try {
                navigator.clipboard.writeText(input.value);
            } catch(e) {
                document.execCommand("copy");
            }
            var btn = document.getElementById("copyBtn");
            btn.innerHTML = "✅ Copied!";
            btn.classList.add("copied");
            setTimeout(function() {
                btn.innerHTML = "📋 Copy Link";
                btn.classList.remove("copied");
            }, 2500);
        }
    </script>
</body>
</html>
'''

@app.route('/v/<video_id>')
def watch_video(video_id):
    print(f"\n{'='*50}")
    print(f"🎬 Video request: {video_id}")
    
    try:
        db = load_db()
    except Exception as e:
        print(f"❌ Database load failed: {e}")
        return "<h2>Database Error</h2>", 500
    
    if video_id not in db:
        print(f"❌ Video ID not found: {video_id}")
        return '''
            <html>
            <head><title>Not Found</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
            .error-box{background:#111;padding:40px;border-radius:20px;border:1px solid #333;}h1{font-size:2em;margin-bottom:10px;}p{color:#888;}</style></head>
            <body><div class="error-box"><h1>🔍 Video Not Found</h1><p>This link may be expired</p></div></body></html>
        ''', 404
    
    video = db[video_id]
    message_id = video.get('message_id')
    
    if not message_id:
        print("❌ No message_id found!")
        return "<h2>Error: Missing message_id</h2>", 500
    
    # Build Telegram channel public link
    # Format: https://t.me/username/message_id
    channel_clean = CHANNEL_USERNAME.replace('@', '')
    tg_message_url = f"https://t.me/{channel_clean}/{message_id}"
    
    print(f"📁 File: {video.get('file_name')}")
    print(f"🔗 Telegram URL: {tg_message_url}")
    
    # Update view count
    try:
        video['views'] = video.get('views', 0) + 1
        save_db(db)
    except:
        pass
    
    # Format size
    size = video.get('size', 0)
    if size > 1024*1024*1024:
        size_str = f"{size/(1024*1024*1024):.1f} GB"
    elif size > 1024*1024:
        size_str = f"{size/(1024*1024):.1f} MB"
    else:
        size_str = f"{size/1024:.1f} KB"
    
    # Render page with Telegram embed
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{video.get('file_name', 'Video')}</title>
        <meta property="og:title" content="{video.get('file_name', 'Video')}">
        <meta property="og:type" content="video.other">
        <meta property="og:url" content="{request.url}">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: #000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 15px;
            }}
            .container {{
                width: 100%;
                max-width: 900px;
                background: #111;
                border-radius: 20px;
                overflow: hidden;
            }}
            .video-section {{
                background: #000;
                position: relative;
                padding-top: 56.25%;
            }}
            .video-section iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: none;
            }}
            .content {{ padding: 25px; }}
            .file-name {{
                color: #fff;
                font-size: 22px;
                font-weight: 700;
                margin-bottom: 8px;
                word-break: break-word;
            }}
            .file-meta {{
                color: #999;
                font-size: 14px;
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
            }}
            .button-group {{
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 14px 28px;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s;
            }}
            .btn-telegram {{
                background: linear-gradient(135deg, #0088cc, #006699);
                color: white;
                flex: 1;
                justify-content: center;
                min-width: 160px;
            }}
            .btn-telegram:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,136,204,0.4);
            }}
            .btn-copy {{
                background: #2a2a2a;
                color: white;
                min-width: 160px;
                justify-content: center;
            }}
            .btn-copy.copied {{
                background: #28a745 !important;
            }}
            .link-box {{
                background: #1a1a1a;
                border: 1px solid #333;
                color: #aaa;
                padding: 14px 18px;
                border-radius: 12px;
                font-size: 14px;
                width: 100%;
                margin-top: 12px;
                word-break: break-all;
                font-family: 'Courier New', monospace;
            }}
            .watermark {{
                text-align: center;
                padding: 15px;
                color: #444;
                font-size: 12px;
            }}
            @media (max-width: 600px) {{
                .content {{ padding: 15px; }}
                .file-name {{ font-size: 17px; }}
                .btn {{ padding: 12px 20px; font-size: 14px; }}
                .button-group {{ flex-direction: column; }}
                .file-meta {{ flex-direction: column; gap: 5px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="video-section">
                <iframe src="https://t.me/{channel_clean}/{message_id}?embed=1" 
                        allowfullscreen 
                        allow="autoplay; fullscreen">
                </iframe>
            </div>
            <div class="content">
                <div class="file-name">📹 {video.get('file_name', 'Video')}</div>
                <div class="file-meta">
                    <span>📦 {size_str}</span>
                    <span>📅 {video.get('date', 'Unknown')}</span>
                    <span>👁️ {video.get('views', 0)} views</span>
                </div>
                <div class="button-group">
                    <a href="{tg_message_url}" target="_blank" class="btn btn-telegram">
                        📱 Open in Telegram
                    </a>
                    <button onclick="copyLink()" class="btn btn-copy" id="copyBtn">
                        📋 Copy Link
                    </button>
                </div>
                <input type="text" class="link-box" id="shareInput" 
                       value="{request.url}" readonly onclick="this.select()">
            </div>
            <div class="watermark">🚀 Powered by Cloud Store • No App Needed</div>
        </div>
        <script>
            function copyLink() {{
                var input = document.getElementById("shareInput");
                input.select();
                navigator.clipboard.writeText(input.value);
                var btn = document.getElementById("copyBtn");
                btn.innerHTML = "✅ Copied!";
                btn.classList.add("copied");
                setTimeout(function() {{
                    btn.innerHTML = "📋 Copy Link";
                    btn.classList.remove("copied");
                }}, 2500);
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/')
def home():
    db = load_db()
    count = len(db)
    return f'''
    <html>
    <head>
        <title>Cloud Store - Video Streaming</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; text-align: center; padding: 20px; }}
            .card {{ background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border-radius: 20px; padding: 50px 40px; border: 1px solid rgba(255,255,255,0.1); }}
            h1 {{ font-size: 3.5em; margin-bottom: 10px; }}
            .count {{ color: #0088cc; font-size: 3em; font-weight: bold; }}
            p {{ color: #888; font-size: 1.2em; margin-top: 10px; }}
            .badge {{ background: #0088cc; color: white; padding: 8px 20px; border-radius: 20px; display: inline-block; margin-top: 20px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="card"><h1>🎬</h1><p>Total Videos</p><div class="count">{count}</div><div class="badge">🚀 Cloud Store • 2GB Support</div></div>
    </body>
    </html>
    '''

# ========== TELEGRAM BOT ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **Cloud Video Store Bot**\n\n"
        "🔹 **How to use:**\n"
        "1️⃣ Forward a video to me\n"
        "2️⃣ Reply with `/genlink`\n"
        "3️⃣ Get a web link instantly!\n\n"
        "🌐 **Features:**\n"
        "✅ Works in any browser\n"
        "✅ No Telegram app needed\n"
        "✅ Up to 2GB files supported\n"
        "✅ Stream via Telegram CDN\n"
        "✅ Mobile responsive\n"
        "✅ View counter\n\n"
        "📤 **Send a video to start!**",
        parse_mode=ParseMode.MARKDOWN
    )

async def genlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ **How to use /genlink:**\n\n"
            "1️⃣ Forward a video to me first\n"
            "2️⃣ Reply to that video with `/genlink`\n\n"
            "*Example:* Reply to a video → type /genlink",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    replied = update.message.reply_to_message
    
    if not replied.video and not replied.document:
        await update.message.reply_text(
            "❌ Please reply to a **video** message!\nOnly videos are supported.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Extract file info
    if replied.video:
        file_id = replied.video.file_id
        file_name = replied.video.file_name or f"video_{uuid.uuid4().hex[:6]}.mp4"
        file_size = replied.video.file_size
        duration = replied.video.duration
    else:
        file_id = replied.document.file_id
        file_name = replied.document.file_name or f"file_{uuid.uuid4().hex[:6]}"
        file_size = replied.document.file_size
        duration = 0
    
    size_mb = file_size / (1024 * 1024)
    
    # Check Telegram limit (2GB)
    if file_size > 2000 * 1024 * 1024:
        await update.message.reply_text(
            f"❌ **File too large!**\n\n"
            f"📦 Size: `{size_mb:.1f} MB`\n"
            f"⚠️ Max: `2000 MB (2GB)`\n\n"
            f"Telegram supports up to 2GB files."
        )
        return
    
    # Processing message
    status_msg = await update.message.reply_text("🔄 Processing...")
    
    try:
        # Forward to channel
        forwarded = await context.bot.forward_message(
            chat_id=CHANNEL_ID,
            from_chat_id=update.effective_chat.id,
            message_id=replied.message_id
        )
        
        message_id = forwarded.message_id
        
        # Generate video ID
        video_id = uuid.uuid4().hex[:8]
        
        # Save to database
        db = load_db()
        db[video_id] = {
            'file_id': file_id,
            'file_name': file_name,
            'size': file_size,
            'duration': duration,
            'message_id': message_id,
            'channel_msg_id': message_id,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'views': 0
        }
        save_db(db)
        
        print(f"✅ Video forwarded to channel: msg_id={message_id}")
        
        # Generate links
        web_link = f"{DOMAIN}/v/{video_id}"
        channel_clean = CHANNEL_USERNAME.replace('@', '')
        tg_link = f"https://t.me/{channel_clean}/{message_id}"
        
        await status_msg.edit_text(
            f"✅ **Link Generated!**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"📦 **Size:** `{size_mb:.1f} MB`\n"
            f"⏱️ **Duration:** `{duration} seconds`\n\n"
            f"🌐 **Web Link:**\n`{web_link}`\n\n"
            f"📱 **Telegram:**\n`{tg_link}`\n\n"
            f"👥 *Share web link - opens in browser!*",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        print(f"❌ Forward error: {e}")
        await status_msg.edit_text(
            f"❌ **Error!**\n\n"
            f"Make sure bot is admin in the channel!\n"
            f"Error: `{str(e)[:100]}`"
        )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    size_mb = video.file_size / (1024 * 1024)
    await update.message.reply_text(
        f"📹 **Video Received!**\n\n"
        f"📁 Name: `{video.file_name or 'Unknown'}`\n"
        f"📦 Size: `{size_mb:.1f} MB`\n"
        f"⏱️ Duration: `{video.duration}s`\n\n"
        f"➡️ **Reply with** `/genlink` **to get web link!**",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type and 'video' in doc.mime_type:
        size_mb = doc.file_size / (1024 * 1024)
        await update.message.reply_text(
            f"📹 **Video File Received!**\n\n"
            f"📁 Name: `{doc.file_name or 'Unknown'}`\n"
            f"📦 Size: `{size_mb:.1f} MB`\n\n"
            f"➡️ **Reply with** `/genlink` **to get web link!**",
            parse_mode=ParseMode.MARKDOWN
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    total_videos = len(db)
    total_views = sum(v.get('views', 0) for v in db.values())
    total_size = sum(v.get('size', 0) for v in db.values())
    size_gb = total_size / (1024*1024*1024)
    
    await update.message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"📹 Total Videos: `{total_videos}`\n"
        f"👁️ Total Views: `{total_views}`\n"
        f"💾 Storage Used: `{size_gb:.2f} GB`\n"
        f"📡 Channel: `{CHANNEL_USERNAME}`\n"
        f"🌐 Domain: `{DOMAIN}`",
        parse_mode=ParseMode.MARKDOWN
    )

def run_bot():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("genlink", genlink))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        print("🤖 Bot is running...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print(traceback.format_exc())

if __name__ == '__main__':
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()
    print("✅ Bot process started")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Web server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
