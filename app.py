import json
import os
import uuid
import requests
import multiprocessing
from datetime import datetime
from flask import Flask, render_template_string, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8884338555:AAEkF8Wbc0G3CFaD3mMpNZWEn7icQNw4DyM")
DOMAIN = os.environ.get("DOMAIN", "https://cloud-h6j7.onrender.com")

# ========== DATABASE ==========
DB_FILE = "videos_db.json"

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
    <meta property="og:image" content="https://i.imgur.com/JLq4rX4.jpg">
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
    db = load_db()
    
    if video_id not in db:
        return '''
            <html>
            <head>
                <title>Not Found</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
                    .error-box{background:#111;padding:40px;border-radius:20px;border:1px solid #333;}
                    h1{font-size:2em;margin-bottom:10px;}
                    p{color:#888;}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>🔍 Video Not Found</h1>
                    <p>This link may be expired or invalid</p>
                </div>
            </body>
            </html>
        ''', 404
    
    video = db[video_id]
    
    try:
        tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={video['file_id']}"
        response = requests.get(tg_url, timeout=15).json()
        
        if not response.get('ok'):
            return '''
                <html>
                <head><title>Error</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
                .error-box{background:#111;padding:40px;border-radius:20px;border:1px solid #333;}
                h1{font-size:2em;margin-bottom:10px;}p{color:#888;}</style></head>
                <body><div class="error-box"><h1>⚠️ Video Unavailable</h1><p>Please try again later</p></div></body></html>
            ''', 500
        
        file_path = response['result']['file_path']
        stream_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
    except Exception as e:
        print(f"Error: {e}")
        return '''
            <html>
            <head><title>Error</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
            .error-box{background:#111;padding:40px;border-radius:20px;border:1px solid #333;}
            h1{font-size:2em;}</style></head>
            <body><div class="error-box"><h1>⚠️ Error Loading</h1><p>Please try again</p></div></body></html>
        ''', 500
    
    # Update view count
    video['views'] = video.get('views', 0) + 1
    save_db(db)
    
    # Format size
    size = video.get('size', 0)
    if size > 1024*1024*1024:
        size_str = f"{size/(1024*1024*1024):.1f} GB"
    elif size > 1024*1024:
        size_str = f"{size/(1024*1024):.1f} MB"
    else:
        size_str = f"{size/1024:.1f} KB"
    
    return render_template_string(
        PLAYER_TEMPLATE,
        video_url=stream_url,
        file_name=video.get('file_name', 'Video'),
        file_size=size_str,
        upload_date=video.get('date', 'Unknown'),
        views=video.get('views', 0),
        share_url=request.url
    )

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
            body {{
                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                text-align: center;
                padding: 20px;
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 50px 40px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            h1 {{ font-size: 3.5em; margin-bottom: 10px; }}
            .count {{ color: #0088cc; font-size: 3em; font-weight: bold; }}
            p {{ color: #888; font-size: 1.2em; margin-top: 10px; }}
            .badge {{
                background: #0088cc;
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                display: inline-block;
                margin-top: 20px;
                font-size: 14px;
            }}
            .features {{
                display: flex;
                gap: 15px;
                margin-top: 25px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            .feature {{
                background: rgba(255,255,255,0.05);
                padding: 15px 20px;
                border-radius: 12px;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎬</h1>
            <p>Total Videos Stored</p>
            <div class="count">{count}</div>
            <div class="features">
                <div class="feature">🌐 Browser Support</div>
                <div class="feature">📱 Mobile Ready</div>
                <div class="feature">⬇️ Download</div>
            </div>
            <div class="badge">🚀 Cloud Store • No App Needed</div>
        </div>
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
        "✅ Stream & Download\n"
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
            "❌ Please reply to a **video** message!\n\n"
            "Only video files are supported.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Extract file info
    if replied.video:
        file_id = replied.video.file_id
        file_name = replied.video.file_name or f"video_{uuid.uuid4().hex[:6]}.mp4"
        file_size = replied.video.file_size
        file_type = replied.video.mime_type or "video/mp4"
        duration = replied.video.duration
    else:
        file_id = replied.document.file_id
        file_name = replied.document.file_name or f"file_{uuid.uuid4().hex[:6]}"
        file_size = replied.document.file_size
        file_type = replied.document.mime_type or "application/octet-stream"
        duration = 0
    
    # Generate ID
    video_id = uuid.uuid4().hex[:8]
    
    # Save to database
    db = load_db()
    db[video_id] = {
        'file_id': file_id,
        'file_name': file_name,
        'size': file_size,
        'mime_type': file_type,
        'duration': duration,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'views': 0
    }
    save_db(db)
    
    # Generate links
    web_link = f"{DOMAIN}/v/{video_id}"
    telegram_link = f"https://t.me/{context.bot.username}?start=video_{video_id}"
    
    # Format size
    size_mb = file_size / (1024 * 1024)
    
    await update.message.reply_text(
        f"✅ **Link Generated Successfully!**\n\n"
        f"📁 **File:** `{file_name}`\n"
        f"📦 **Size:** `{size_mb:.1f} MB`\n"
        f"⏱️ **Duration:** `{duration} seconds`\n\n"
        f"🌐 **Web Link (Share Anyone):**\n"
        f"`{web_link}`\n\n"
        f"📱 **Telegram Link:**\n"
        f"`{telegram_link}`\n\n"
        f"👥 *Anyone can open web link in browser!*\n"
        f"📲 *No Telegram app required!*",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    size_mb = video.file_size / (1024 * 1024)
    duration = video.duration
    
    await update.message.reply_text(
        f"📹 **Video Received!**\n\n"
        f"📁 Name: `{video.file_name or 'Unknown'}`\n"
        f"📦 Size: `{size_mb:.1f} MB`\n"
        f"⏱️ Duration: `{duration}s`\n\n"
        f"➡️ **Reply with** `/genlink` **to get web link!**\n"
        f"🌐 Anyone can watch it in browser!",
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
            f"➡️ **Reply with** `/genlink` **to get web link!**\n"
            f"🌐 Anyone can watch it in browser!",
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
        f"💾 Storage Used: `{size_gb:.2f} GB`\n\n"
        f"🌐 **Domain:** `{DOMAIN}`",
        parse_mode=ParseMode.MARKDOWN
    )

def run_bot():
    """Run Telegram bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("genlink", genlink))
    application.add_handler(CommandHandler("stats", stats))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Bot is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    # Run bot in separate process
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()
    print("✅ Bot process started")
    
    # Run Flask web server
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Web server starting on port {port}")
    app.run(host='0.0.0.0', port=port)
