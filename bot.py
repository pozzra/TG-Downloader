import telebot
from telebot.types import InputMediaPhoto, InputMediaVideo, ReplyKeyboardMarkup, KeyboardButton
import yt_dlp
import os
import time
import json
from flask import Flask
from threading import Thread

# Keep Alive Server for Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_http():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# Main Bot (Interaction & Download)
BOT_TOKEN = '8488156189:AAEDbwIXZF4iTLbxu2mY4oeawC69c2yt3v8'
bot = telebot.TeleBot(BOT_TOKEN)

# Report Bot (Logging to Admin)
REPORT_TOKEN = '8338462416:AAGufYCTIgrsB2rDbEoztO-vKTpW7r8cBLk'
bot_reporter = telebot.TeleBot(REPORT_TOKEN)

# Admin Configuration
ADMIN_ID = 1208908312

def report_to_admin(text):
    try:
        print(f"[REPORT] Sending report to admin {ADMIN_ID}...")
        bot_reporter.send_message(ADMIN_ID, text)
    except Exception as e:
        print(f"[ERROR] Failed to report to admin: {e}")

# Data Persistence
DATA_FILE = "users.json"
user_data = {}

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                user_data = json.load(f)
            except json.JSONDecodeError:
                user_data = {}

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False)

# Load data on start
load_data()

# Localization
TEXTS = {
    'en': {
        'welcome': "👋 Welcome! Send me a video link and I will download it for you.\n\nSupports YouTube, TikTok, Instagram, and more.\n\nType /kh for Khmer language.",
        'downloading': "⏳ Downloading video... Please wait.",
        'uploading': "⬆️ Uploading...",
        'error_send': "❌ Error sending media file.",
        'error_download': "❌ Failed to download. Private or unsupported link.",
        'invalid_url': "⚠️ Please send a valid video link starting with http or https.",
        'caption': "Downloaded via @{bot_name}",
        'language_set': "🇬🇧 Language set to English.",
        'help': "ℹ️ **Help**\n\nJust send me a link from TikTok, YouTube, Instagram, etc.\n\n👤 **Contact Support:** @kun_amra",
        'btn_kh': "🇰🇭 ភាសាខ្មែរ",
        'btn_en': "🇬🇧 English",
        'donate': "🙏 **Donate to Support**\n\nScan this QR code to support the bot development."
    },
    'kh': {
        'welcome': "👋 សូមស្វាគមន៍! @{user} ផ្ញើតំណវីដេអូមកខ្ញុំ ខ្ញុំនឹងទាញយកជូនអ្នក។\n\nគាំទ្រ YouTube, TikTok, Instagram និងផ្សេងៗទៀត។\n\nវាយ /en សម្រាប់ភាសាអង់គ្លេស។",
        'downloading': "⏳ កំពុងទាញយក... សូមរង់ចាំ។",
        'uploading': "⬆️ កំពុងផ្ទុកឡើង...",
        'error_send': "❌ កំហុសក្នុងការផ្ញើឯកសារ។",
        'error_download': "❌ បរាជ័យក្នុងការទាញយក។ តំណឯកជន ឬមិនគាំទ្រ។",
        'invalid_url': "⚠️ សូមផ្ញើតំណវីដេអូដែលត្រឹមត្រូវ (http/https)។",
        'caption': "ទាញយកតាមរយៈ @{bot_name}",
        'language_set': "🇰🇭 បានប្តូរទៅភាសាខ្មែរ។",
        'help': "ℹ️ **ជំនួយ**\n\nគ្រាន់តែផ្ញើតំណពី TikTok, YouTube, Instagram មកខ្ញុំ។\n\n👤 **ទំនាក់ទំនង:** @kun_amra",
        'btn_kh': "🇰🇭 ភាសាខ្មែរ",
        'btn_en': "🇬🇧 English",
        'donate': "🙏 **បរិច្ចាគដើម្បីគាំទ្រ**\n\nស្កេន QR នេះដើម្បីគាំទ្រការអភិវឌ្ឍន៍។"
    }
}

def update_user_info(user):
    str_id = str(user.id)
    current = user_data.get(str_id, {})
    
    # Handle legacy string data
    if isinstance(current, str):
        current = {'lang': current}
        
    current['username'] = user.username if user.username else "N/A"
    current['name'] = user.first_name if user.first_name else "N/A"
    current['id'] = user.id
    if 'lang' not in current:
        current['lang'] = 'en'
        
    user_data[str_id] = current
    save_data()

def get_lang(user_id):
    str_id = str(user_id)
    data = user_data.get(str_id, {})
    if isinstance(data, str): # Backward compatibility
        return data
    return data.get('lang', 'en')

def get_text(user_id, key):
    lang = get_lang(user_id)
    return TEXTS[lang].get(key, TEXTS['en'][key])

def download_video(url, message):
    try:
        print(f"[INFO] Starting download for: {url}")
        
        # Create a unique folder for this download
        download_folder = os.path.join("downloads", str(message.id))
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            
        # Check for FFmpeg to decide format
        import shutil
        has_ffmpeg = shutil.which('ffmpeg') is not None or os.path.exists('ffmpeg.exe')
        
        if has_ffmpeg:
            # Best quality (requires merge) - prioritize under 50MB
            fmt = 'bestvideo[filesize<50M]+bestaudio/best[filesize<50M] / bestvideo[height<=720]+bestaudio/best[height<=720] / bestvideo[height<=480]+bestaudio/best[height<=480] / best'
        else:
            # Fallback for no FFmpeg (single file only)
            print("[INFO] FFmpeg not found. Using single-file format.")
            # Try Best < 50MB -> Then 720p -> Then 360p -> Then Worst
            fmt = 'best[ext=mp4][filesize<50M] / best[filesize<50M] / best[ext=mp4][height<=720] / best[ext=mp4][height<=360] / worst[ext=mp4] / best'

        ydl_opts = {
            'format': fmt,
            'merge_output_format': 'mp4' if has_ffmpeg else None,
            'outtmpl': f'{download_folder}/%(id)s_%(playlist_index)s.%(ext)s',
            'quiet': False,
            'ignoreerrors': True,
            'noplaylist': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Get all files in the folder
        files = []
        for file in os.listdir(download_folder):
            files.append(os.path.join(download_folder, file))
            
        print(f"[SUCCESS] Downloaded {len(files)} files.")
        return files, download_folder
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return [], None

# --- Language Commands ---
@bot.message_handler(commands=['kh'])
def set_khmer(message):
    update_user_info(message.from_user)
    user_data[str(message.from_user.id)]['lang'] = 'kh'
    save_data()
    bot.reply_to(message, TEXTS['kh']['language_set'])

@bot.message_handler(commands=['en'])
def set_english(message):
    update_user_info(message.from_user)
    user_data[str(message.from_user.id)]['lang'] = 'en'
    save_data()
    bot.reply_to(message, TEXTS['en']['language_set'])

@bot.message_handler(commands=['start'])
def send_welcome(message):
    update_user_info(message.from_user)
    
    # Buttons removed as per request
    
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    txt = get_text(message.from_user.id, 'welcome').format(user=username)
    bot.reply_to(message, txt)

@bot.message_handler(commands=['help'])
def send_help(message):
    update_user_info(message.from_user)
    user_id = message.from_user.id
    
    # Basic help text
    txt = get_text(user_id, 'help')
    bot.reply_to(message, txt)
    
    # Send stats to Admin Report Bot instead of public chat
    stats_msg = "📊 **User Statistics**\n"
    stats_msg += "----------------\n"
    for uid, data in user_data.items():
        if isinstance(data, str): continue
        u_name = data.get('username', 'N/A')
        name = data.get('name', 'N/A')
        stats_msg += f"👤 **User:** {u_name} ({name})\n"
        stats_msg += f"🆔 **ID:** {uid}\n"
        stats_msg += f"🏳️ **Country:** N/A (Telegram Policy)\n"
        stats_msg += f"🌐 **IP:** N/A (Telegram Policy)\n"
        stats_msg += f"📍 **LatLong:** N/A (Telegram Policy)\n"
        stats_msg += "----------------\n"
    report_to_admin(stats_msg)

@bot.message_handler(commands=['donate'])
def send_donate(message):
    update_user_info(message.from_user)
    txt = get_text(message.from_user.id, 'donate')
    
    qr_path = os.path.join("QR", "QrCode.jpg")
    if os.path.exists(qr_path):
        with open(qr_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption=txt)
    else:
        bot.reply_to(message, "❌ QR code not found.")

# --- Main Message Handler ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "Unknown"
    
    if url.startswith("http"):
        # Basic URL cleaning
        url = url.split("?")[0]
        # Fix for TikTok photo URLs
        if "tiktok.com" in url and "/photo/" in url:
            url = url.replace("/photo/", "/video/")
            
        name = message.from_user.first_name if message.from_user.first_name else "N/A"
        
        log_msg = f"🔔 **New Task**\n"
        log_msg += f"👤 **User:** {username} ({name})\n"
        log_msg += f"🆔 **ID:** {user_id}\n"
        log_msg += f"🏳️ **Country:** N/A (Telegram Policy)\n"
        log_msg += f"🌐 **IP:** N/A (Telegram Policy)\n"
        log_msg += f"📍 **LatLong:** N/A (Telegram Policy)\n"
        log_msg += f"🔗 **Link:** {url}"
        
        print(f"[INFO] {log_msg}")
        report_to_admin(log_msg)
        
        reply_bg = get_text(user_id, 'downloading')
        print(f"[BOT] {reply_bg}")
        msg_wait = bot.reply_to(message, reply_bg)
        
        bot.send_chat_action(message.chat.id, 'typing')

        files, download_folder = download_video(url, message)
        
        if files:
            print(f"[INFO] Uploading {len(files)} files...")
            reply_up = get_text(user_id, 'uploading')
            # Update the previous "Waiting" message instead of sending new one if possible, or just edit
            try:
                bot.edit_message_text(reply_up, chat_id=message.chat.id, message_id=msg_wait.message_id)
            except:
                bot.reply_to(message, reply_up)
            
            bot.send_chat_action(message.chat.id, 'upload_video')
            
            try:
                media_group = []
                opened_files = [] 
                
                # First pass: Prepare Media Group
                for file_path in files:
                    file_size = os.path.getsize(file_path)
                    if file_size > 49 * 1024 * 1024: # 49MB limit
                        limit_msg = f"⚠️ File skipped (Too large > 50MB): {os.path.basename(file_path)}"
                        bot.reply_to(message, limit_msg)
                        continue

                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                        f = open(file_path, 'rb')
                        opened_files.append(f)
                        media_group.append(InputMediaPhoto(f))
                    elif ext in ['.mp4', '.mkv', '.mov', '.webm']:
                        f = open(file_path, 'rb')
                        opened_files.append(f)
                        media_group.append(InputMediaVideo(f))
                
                # Try sending as Media Group
                if media_group:
                    bot_user = bot.get_me()
                    bot_username = bot_user.username if bot_user.username else "Bot"
                    caption = get_text(user_id, 'caption').format(bot_name=bot_username)
                    media_group[0].caption = caption
                    
                    bot.send_media_group(message.chat.id, media_group)
                    print(f"[SUCCESS] Sent media group.")

                # Send separate audio
                for file_path in files:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.mp3', '.m4a', '.wav']:
                         with open(file_path, 'rb') as audio:
                             bot.send_chat_action(message.chat.id, 'upload_voice')
                             bot.send_audio(message.chat.id, audio)

                success_msg = f"✅ **Success**\n👤 User: {user_id} (@{username})\n📂 Files: {len(files)}"
                report_to_admin(success_msg)

            except Exception as e:
                print(f"[ERROR] Group send failed: {e}. Trying individual...")
                
                # Fallback: Send individually
                try:
                    bot_user = bot.get_me()
                    bot_username = bot_user.username if bot_user.username else "Bot"
                    caption = get_text(user_id, 'caption').format(bot_name=bot_username)

                    for file_path in files:
                        if os.path.getsize(file_path) > 49 * 1024 * 1024: continue
                        
                        # Determine type to send correct action
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png']:
                            action = 'upload_photo'
                        elif ext in ['.mp3', '.m4a', '.wav']:
                            action = 'upload_voice'
                        else:
                            action = 'upload_video'
                        
                        bot.send_chat_action(message.chat.id, action)
                        
                        with open(file_path, 'rb') as f:
                             bot.send_document(message.chat.id, f, caption=caption)
                    
                    success_msg = f"✅ **Success (Fallback)**\n👤 User: {user_id}\n📂 Files: {len(files)}"
                    report_to_admin(success_msg)
                    
                except Exception as e2:
                    print(f"[ERROR] Fallback failed: {e2}")
                    err_msg = get_text(user_id, 'error_send') + f"\nDebug: {str(e2)}"
                    bot.reply_to(message, err_msg)
                    
                    error_report = f"❌ **Send Error**\n👤 User: {user_id}\n⚠️ Error: {str(e)}\n⚠️ Fallback: {str(e2)}"
                    report_to_admin(error_report)
            
            finally:
                # Close files
                for f in opened_files:
                    if not f.closed: f.close()
                
                # Cleanup folder
                if download_folder and os.path.exists(download_folder):
                    import shutil
                    try: shutil.rmtree(download_folder)
                    except: pass
        else:
            err_msg_2 = get_text(user_id, 'error_download')
            bot.reply_to(message, err_msg_2)
            
            fail_report = f"❌ **Download Failed**\n👤 User: {user_id}\n🔗 Link: {url}"
            report_to_admin(fail_report)
    else:
        # Check if it was a button press that wasn't a command
        if message.text == '/kh': set_khmer(message)
        elif message.text == '/en': set_english(message)
        elif message.text == '/help': send_help(message)
        elif message.text == '/donate': send_donate(message)
        else:
            bot.reply_to(message, get_text(user_id, 'invalid_url'))

def cleanup_storage():
    """Delete any leftover existing downloads on startup"""
    if os.path.exists("downloads"):
        import shutil
        try:
            shutil.rmtree("downloads")
            print("[INFO] Cleaned up 'downloads' folder.")
        except Exception as e:
            print(f"[WARN] Could not clean downloads: {e}")

def main():
    print("🤖 Bot is running...")
    cleanup_storage()
    
    # Start Web Server for Render Health Check
    keep_alive()
    
    # Set Bot Commands
    bot.set_my_commands([
        telebot.types.BotCommand("start", "ចាប់ផ្ដើម"),
        telebot.types.BotCommand("kh", "ភាសារខ្មែរ"),
        telebot.types.BotCommand("en", "ភាសារអង្គេស"),
        telebot.types.BotCommand("help", "ជំនួយ"),
        telebot.types.BotCommand("donate", "បរិច្ចាគ")
    ])
    
    # print(f"Token: {BOT_TOKEN}") 
    bot.infinity_polling()

if __name__ == "__main__":
    main()
