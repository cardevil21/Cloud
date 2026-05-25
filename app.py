import json
import os
import uuid
import requests
import threading
from datetime import datetime
from flask import Flask, render_template_string, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== CONFIGURATION ==========
BOT_TOKEN = "8884338555:AAEkF8Wbc0G3CFaD3mMpNZWEn7icQNw4DyM"
DOMAIN = "https://your-app.onrender.com"  # Deploy-এর পর update করবেন

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
        .video-section {
            background: #000;
            position: relative;
        }
        video {
            width: 100%;
            display: block;
            max-height: 75vh;
            outline: none;
        }
        .content {
            padding: 25px;
        }
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
            background: #0088cc;
            color: white;
            flex: 1;
            justify-content: center;
            min-width: 150px;
        }
        .btn-download:hover {
            background: #0077b3;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,136,204,0.3);
        }
        .btn-copy {
            background: #2a2a2a;
            color: white;
            min-width: 150px;
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
        @media (max-width: 600px) {
            .content { padding: 15px; }
            .file-name { font-size: 17px; }
            .btn { padding: 12px 20px; font-size: 14px; }
            .button-group { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="video-section">
            <video controls autoplay playsinline controlsList="nodownload">
                <source src="{{ video_url }}" type="video/mp4">
                Your browser does not support video.
            </video>
        </div>
        <div class="content">
            <div class="file-name">📹 {{ file_name }}</div>
            <div class="file-meta">
                📦 {{ file_size }} • 📅 {{ upload_date }} • 👁️ {{ views }} views
            </div>
            <div class="button-group">
                <a href="{{ video_url }}" download="{{ file_name }}" class="btn btn-download">
                    ⬇ Download Video
                </a>
                <button onclick="copyShareLink()" class="btn btn-copy" id="copyBtn">
                    📋 Copy Link
                </button>
            </div>
            <input type="text" class="link-box" id="shareInput" 
                   value="{{ share_url }}" readonly onclick="this.select()">
        </div>
    </div>

    <script>
        function copyShareLink() {
            var input = document.getElementById("shareInput");
            input.select();
            input.setSelectionRange(0, 99999);
            
            try {
                navigator.clipboard.writeText(input.value);
            } catch(e) {
                document.execCommand("copy");
            }
            
            var btn = document.getElementById("copyBtn");
            btn.textContent = "✅ Copied!";
            btn.classList.add("copied");
            
            setTimeout(function() {
                btn.textContent = "📋 Copy Link";
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
            <html><head><title>Not Found</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
            h1{font-size:2em} p{color:#888;margin-top:10px}</style></head>
            <body><div><h1>🔍 Video Not Found</h1><p>This link might be expired or invalid</p></div></body></html>
        ''', 404
    
    video = db[video_id]
    
    try:
        # Get file path from Telegram
        tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={video['file_id']}"
        response = requests.get(tg_url, timeout=15).json()
        
        if not response.get('ok'):
            return '''
                <html><head><title>Error</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>body{background:#000;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial;text-align:center;}
                h1{font-size:2em} p{color:#888;margin-top:10px}</style></head>
                <body><div><h1>⚠️ Video Unavailable</h1><p>Please try again later</p></div></body></html>
            ''', 500
        
        file_path = response['result']['file_path']
        stream_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
    except Exception as e:
        return f'''
            <html><head><title>Error</title></head>
            <body style="background:#000;color:white;text-align:center;padding-top:50px;">
            <h1>⚠️ Error Loading Video</h1><p>Please try again</p></body></html>
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
        file_name=video.get('file_name', 'Untitled Video'),
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
        <title>Video Store</title>
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
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎬</h1>
            <p>Total Videos</p>
            <div class="count">{count}</div>
            <div class="badge">🚀 Powered by Telegram</div>
        </div>
    </body>
    </html>
    '''

# ========== TELEGRAM BOT ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **Welcome to Video Store Bot!**\n\n"
        "🔹 Forward a video to me\n"
        "🔹 Reply with `/genlink`\n"
        "🔹 Get a web link that anyone can open!\n\n"
        "🌐 *No app needed - works in browser*\n"
        "📱 *Share with anyone*\n"
        "⬇️ *Stream & Download*\n\n"
        "**Send a video to get started!**",
        parse_mode=ParseMode.MARKDOWN
    )

async def genlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ **How to use /genlink:**\n\n"
            "1️⃣ First forward a video to me\n"
            "2️⃣ Then reply to that video with `/genlink`\n\n"
            "*Example:* Reply to video → type /genlink",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    replied = update.message.reply_to_message
    if not replied.video and not replied.document:
        await update.message.reply_text(
            "❌ Please reply to a **video** message!\n"
            "Only videos are supported for streaming.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if replied.video:
        file_id = replied.video.file_id
        file_name = replied.video.file_name or f"video_{uuid.uuid4().hex[:6]}.mp4"
        file_size = replied.video.file_size
        file_type = replied.video.mime_type or "video/mp4"
    else:
        file_id = replied.document.file_id
        file_name = replied.document.file_name or f"file_{uuid.uuid4().hex[:6]}"
        file_size = replied.document.file_size
        file_type = replied.document.mime_type or "application/octet-stream"
    
    video_id = uuid.uuid4().hex[:8]
    
    db = load_db()
    db[video_id] = {
        'file_id': file_id,
        'file_name': file_name,
        'size': file_size,
        'mime_type': file_type,
        'date': datetime.now().strftime("%Y-%m-%d"),
        'views': 0
    }
    save_db(db)
    
    web_link = f"{DOMAIN}/v/{video_id}"
    
    await update.message.reply_text(
        f"✅ **Link Generated Successfully!**\n\n"
        f"📁 **File:** `{file_name}`\n"
        f"📦 **Size:** `{file_size/(1024*1024):.1f} MB`\n\n"
        f"🔗 **Watch Link:**\n`{web_link}`\n\n"
        f"👥 *Anyone can open this link in browser*\n"
        f"🌐 *No Telegram app needed!*",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📹 **Video received!**\n\n"
        "To generate a shareable web link:\n"
        "➡️ Reply to this video with `/genlink`\n\n"
        "The link will work in any browser! 🌐",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type and 'video' in doc.mime_type:
        await update.message.reply_text(
            "📹 **Video file received!**\n\n"
            "➡️ Reply to this message with `/genlink`\n"
            "to get a shareable web link! 🌐",
            parse_mode=ParseMode.MARKDOWN
        )

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("genlink", genlink))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Bot is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
