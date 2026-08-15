"""
قحطان - بوت ذكاء اصطناعي متعدد المواهب
نسخة محسنة v5.0
"""

import logging
import os
import re
import time
import asyncio
import json
import base64
import random
import platform
import shutil
import socket
from io import BytesIO
from threading import Thread
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import yt_dlp
import requests
from datetime import datetime

load_dotenv()
from features import register_feature_handlers, handle_feature_text
from utility_features import register_utility_handlers
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== الإعدادات ==============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
DEVELOPER_IDS = {
    int(value.strip())
    for value in os.environ.get("DEVELOPER_IDS", "").split(",")
    if value.strip().isdigit()
}
BOT_NAME = "Qahtan"
BOT_VERSION = "5.2.0"
PORT = int(os.environ.get("BOT_PORT", os.environ.get("PORT", 8080)))
NODE_SERVER_PORT = int(os.environ.get("NODE_SERVER_PORT", 3000))
NODE_SERVER_URL = os.environ.get("NODE_SERVER_URL", f"http://127.0.0.1:{NODE_SERVER_PORT}").rstrip("/")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
MENU_ANIMATION_PATH = os.path.join(ASSET_DIR, "qahtan_menu.gif")

MAX_MSG = 4000
RATE_MSGS = 15
RATE_WIN = 60
MAX_HISTORY = 15

flask_app = Flask(__name__)
bot_start_time = time.time()

# ============== الحالة ==============
dev_mode_active = {}
user_dialect = {}
user_message_count = defaultdict(int)
user_rate = defaultdict(list)
banned_users = set()
user_personality = {}
conversation_history = defaultdict(list)
user_stats = defaultdict(lambda: {"messages": 0, "start_time": time.time()})
bot_stats = {"messages": 0, "users": set(), "errors": 0}

# ============== وضع المطور ==============
DEVELOPER_MODE_CODE = "505"
dev_mode_users = set()
dev_pending_code = {}  # المستخدمين الذين يدخلون الكود

# ============== الشخصيات ==============
PERSONALITIES = {
    "normal": "أنت بوت ذكي متحدث باسم 'قحطان'. رد بشكل طبيعي وودي ومفيد.",
    "funny": "أنت بوت كوميدي اسمك 'قحطان'. رد بفكاهة ونكت ومسليات.",
    "serious": "أنت بوت جدي ومحترف اسمك 'قحطان'. قدم معلومات دقيقة وموثوقة.",
    "poet": "أنت شاعر عربي اسمك 'قحطان'. اكتب أبيات شعرية في ردودك.",
    "detective": "أنت محقق خاص اسمك 'قحطان'. حلل الأمور بعمق ودقة.",
    "teacher": "أنت معلم متخصص اسمك 'قحطان'. اشرح بطريقة واضحة وبسيطة.",
    "philosopher": "أنت فيلسوف حكيم اسمك 'قحطان'. فكر بعمق وشارك حكم.",
    "hacker": "أنت هاكر أخلاقي اسمك 'قحطان'. ساعد في أمور التقنية والأمن.",
    "doctor": "أنت طبيب حكيم اسمك 'قحطان'. قدم نصائح صحية.",
    "chef": "أنت طاهٍ محترف اسمك 'قحطان'. شارك وصفات طبخ لذيذة.",
    "coach": "أنت مدرب حياة اسمك 'قحطان'. قدم نصائح للتطوير الذاتي.",
    "news": "أنت صحفي مخضرم اسمك 'قحطان'. اقدم أخباراً وتحليلات.",
    "legal": "أنت محامي قانوني اسمك 'قحطان'. اشرح أمور قانونية.",
    "tech": "أنت خبير تقنية اسمك 'قحطان'. ساعد في البرمجة والتكنولوجيا.",
    "game": "أنت لاعب محترف اسمك 'قحطان'. تحدث عن الألعاب.",
    "movies": "أنت ناقد سينمائي اسمك 'قحطان'. راجع الأفلام والمسلسلات.",
    "music": "أنت خبير موسيقى اسمك 'قحطان'. تحدث عن الموسيقى.",
    "sports": "أنت محلل رياضي اسمك 'قحطان'. اكتب عن الرياضات.",
    "islam": "أنت عالم دين اسمك 'قحطان'. أجب على أسئلة الشرعية.",
    "history": "أنت مؤرخ اسمك 'قحطان'. شارك معلومات تاريخية.",
}

PERS_AR = {
    "normal": "عادي", "funny": "مضحك", "serious": "جدي",
    "poet": "شاعر", "detective": "محقق", "teacher": "معلم",
    "philosopher": "فيلسوف", "hacker": "هاكر", "doctor": "طبيب",
    "chef": "طاهٍ", "coach": "مدرب", "news": "صحفي",
    "legal": "محامي", "tech": "تقني", "game": "لاعب",
    "movies": "ناقد", "music": "موسيقي", "sports": "رياضي",
    "islam": "ديني", "history": "مؤرخ"
}

DIALECTS_AR = {
    "saudi": "سعودي", "iraqi": "عراقي", "kuwaiti": "كويتي",
    "yemeni": "يمني", "emirati": "إماراتي", "egyptian": "مصري",
    "jordanian": "أردني", "lebanese": "لبناني", "syrian": "سوري",
    "palestinian": "فلسطيني"
}
# ============== Music Search ==============
music_search_results = {}  # user_id -> list of results
music_search_mode = set()  # users waiting for music search

def search_youtube(query, limit=5):
    import yt_dlp
    ydl_opts = {'noplaylist': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            return [{"title": r["title"], "id": r["id"]} for r in results.get("entries", [])]
    except Exception as e:
        print(f"Search error: {e}")
        return []

def download_audio(video_id, filename="temp_audio"):
    import yt_dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{filename}.webm',
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com/watch?v={video_id}"])
        return f"{filename}.webm"
    except Exception as e:
        print(f"Download error: {e}")
        return None

def get_direct_audio_url(video_id):
    import yt_dlp
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'nocheckcertificate': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
            # Try to get direct URL
            for fmt in info.get('formats', []):
                if fmt.get('ext') == 'm4a' or 'audio' in fmt.get('format_note', ''):
                    return fmt.get('url', '')
            return info.get('url', '')
    except Exception as e:
        print(f"Get URL error: {e}")
        return ""

# ============== Music Command ==============
async def music_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اكتب اسم الاغنية للبحث:")

async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    await update.message.reply_text(f"جاري البحث عن: {query}...")
    
    results = search_youtube(query, 5)
    if not results:
        await update.message.reply_text("ما لقيت نتائج!")
        return
    
    music_search_results[update.effective_user.id] = results
    
    kb = []
    for i, r in enumerate(results):
        kb.append([InlineKeyboardButton(r["title"][:40], callback_data=f"music_{i}")])
    kb.append([InlineKeyboardButton("رجوع", callback_data="cb_back")])
    
    await update.message.reply_text("اختر الاغنية:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_music_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if not query.data.startswith("music_"):
        return
    
    index = int(query.data.split("_")[1])
    results = music_search_results.get(uid, [])
    
    if index >= len(results):
        await query.message.reply_text("حدث خطأ!")
        return
    
    result = results[index]
    await query.message.reply_text(f"جاري تحميل: {result['title']}...")
    
    # Download audio
    audio_file = download_audio(result["id"], f"audio_{uid}")
    
    if audio_file:
        try:
            with open(audio_file, "rb") as f:
                await context.bot.send_voice(chat_id=uid, voice=f, caption=result["title"][:200])
            # Clean up
            import os
            os.remove(audio_file)
        except Exception as e:
            await query.message.reply_text(f"خطأ في الإرسال: {str(e)[:100]}")
            # Try sending as audio file
            try:
                with open(audio_file, "rb") as f:
                    await context.bot.send_audio(chat_id=uid, audio=f, title=result["title"][:200])
                os.remove(audio_file)
            except:
                pass
    else:
        # Fallback to YouTube link
        youtube_link = f"https://youtube.com/watch?v={result['id']}"
        kb = [[InlineKeyboardButton("يوتيوب", url=youtube_link)]]
        await query.message.reply_text("ماقدر أتحكم، خذ الرابط:", reply_markup=InlineKeyboardMarkup(kb))
    
    # Clean up
    if uid in music_search_results:
        del music_search_results[uid]

# ============== Flask ==============
@flask_app.route("/")
def home():
    return jsonify({
        "name": BOT_NAME,
        "version": BOT_VERSION,
        "status": "running",
        "uptime": int(time.time() - bot_start_time)
    })

@flask_app.route("/health")
def health():
    return jsonify({"status": "ok", "uptime": int(time.time() - bot_start_time)})

@flask_app.route("/stats")
def stats():
    return jsonify({
        "total_messages": bot_stats["messages"],
        "total_users": len(bot_stats["users"]),
        "errors": bot_stats["errors"]
    })

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, use_reloader=False)

# ============== الدوال المساعدة ==============
def is_rate_limited(uid):
    now = time.time()
    user_rate[uid] = [t for t in user_rate[uid] if now - t < RATE_WIN]
    if len(user_rate[uid]) >= RATE_MSGS:
        return True
    user_rate[uid].append(now)
    return False

def is_dev(uid): return uid in DEVELOPER_IDS


def validate_configuration():
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not DEVELOPER_IDS:
        logger.warning("DEVELOPER_IDS is empty; developer commands are disabled")
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def node_server_health():
    try:
        response = requests.get(f"{NODE_SERVER_URL}/api/health", timeout=3)
        return response.ok, response.json()
    except requests.RequestException as exc:
        logger.warning("Node server health check failed: %s", exc)
        return False, {"status": "unreachable"}


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.exception("Failed to remove temporary file: %s", path)
def split_msg(text): return [text[i:i+MAX_MSG] for i in range(0, len(text), MAX_MSG)]
def fmt_uptime(s): return f"{s//3600}h {(s%3600)//60}m {s%60}s"

def get_system_message(uid):
    pers_key = user_personality.get(uid, "normal")
    dialect_key = user_dialect.get(uid, "saudi")
    dialect_name = DIALECTS_AR.get(dialect_key, "سعودي")
    personality = PERSONALITIES.get(pers_key, PERSONALITIES["normal"])
    return f"{personality}\nتحدث باللهجة {dialect_name}.\nالمطور: @rccjc"

# ============== الذكاء الاصطناعي ==============
def ask_groq(messages):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 600,
            "temperature": 0.7,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.ok:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "") or "عذراً، لم يصل رد من نموذج الذكاء الاصطناعي."
        logger.error("Groq Error %s: %s", response.status_code, response.text[:300])
        return "عذراً، حدث خطأ في خدمة الذكاء الاصطناعي. حاول لاحقاً."
    except requests.RequestException as exc:
        logger.error("Groq network error: %s", exc)
        return "تعذر الاتصال بخدمة الذكاء الاصطناعي حالياً."
    except Exception:
        logger.exception("Unexpected AI error")
        return "عذراً، حدث خطأ. حاول لاحقاً."


async def get_ai_response(uid, text):
    try:
        messages = [{"role": "system", "content": get_system_message(uid)}]
        messages.extend(conversation_history[uid][-MAX_HISTORY:])
        messages.append({"role": "user", "content": text})
        response = await asyncio.to_thread(ask_groq, messages)
        conversation_history[uid].extend([
            {"role": "user", "content": text},
            {"role": "assistant", "content": response},
        ])
        conversation_history[uid] = conversation_history[uid][-MAX_HISTORY * 2:]
        return response
    except Exception:
        logger.exception("AI response error")
        return "عذراً، حدث خطأ. حاول لاحقاً."

# ============== رسالة الترحيب ==============
def get_welcome_html():
    return """<b>❤️ مرحباً بك في قحطان ❤️</b>

<i>بوت ذكاء اصطناعي متعدد المواهب</i>

<b>✨ المميزات:</b>
- محادثة ذكية فائقة
- 20 شخصية متنوعة
- 10 لهجات عربية
- لوحة تحكم المطور

<b>🚀 ابدأ الآن:</b>
ارسل رسالتك وسأرد عليك فوراً

<b>by: @rccjc</b>"""

# ============== أوامر البوت ==============
async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in dev_mode_users:
        kb = [
            [InlineKeyboardButton("إذاعة", callback_data="dev_broadcast"), InlineKeyboardButton("حظر مستخدم", callback_data="dev_ban")],
            [InlineKeyboardButton("إلغاء الحظر", callback_data="dev_unban"), InlineKeyboardButton("إحصائيات شاملة", callback_data="dev_stats")],
            [InlineKeyboardButton("قائمة المستخدمين", callback_data="dev_users"), InlineKeyboardButton("تحميل الكود", callback_data="dev_getcode")],
            [InlineKeyboardButton("إيقاف البوت", callback_data="dev_shutdown"), InlineKeyboardButton("رجوع", callback_data="cb_back")],
        ]
        await update.message.reply_text("لوحة تحكم المطور", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("أدخل رمز المطور:")
        dev_pending_code[uid] = "dev_code"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_stats[uid]["start_time"] = time.time()
    
    welcome = """أهلاً بك في قحطان v5.2.0

أنا بوت ذكاء اصطناعي متعدد المواهب:
- محادثة ذكية مع ذاكرة مؤقتة
- شخصيات ولهجات عربية متعددة
- بحث وتحميل المقاطع الصوتية
- أدوات للمستخدم والمطور

اختر من القائمة أو أرسل رسالتك مباشرة."""
    
    # Modern buttons with different layouts
    kb = [
        # Row 1 - Main actions
        [InlineKeyboardButton("محادثة ذكية", callback_data="cb_chat")],
        # Row 2 - Music
        [InlineKeyboardButton("بحث اغاني", callback_data="cb_music")],
        # Row 3 - Additional features
        [InlineKeyboardButton("ميزات إضافية", callback_data="feature:menu")],
        # Row 4 - Personalization
        [InlineKeyboardButton("تغيير الشخصية", callback_data="cb_personality"), 
         InlineKeyboardButton("تغيير اللهجة", callback_data="cb_dialect")],
        # Row 4 - Info
        [InlineKeyboardButton("إحصائياتي", callback_data="cb_mystats"), 
         InlineKeyboardButton("مساعدة", callback_data="cb_help")],
        # Row 5 - Developer
        [InlineKeyboardButton("لوحة المطور", callback_data="cb_dev")],
    ]
    
    # GIF جون سنو المتحرك يحمل رسالة الترحيب وقائمة الأزرار.
    try:
        if os.path.exists(MENU_ANIMATION_PATH):
            with open(MENU_ANIMATION_PATH, "rb") as gif:
                await update.message.reply_animation(
                    animation=gif,
                    caption=welcome,
                    reply_markup=InlineKeyboardMarkup(kb),
                )
        else:
            await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(kb))
    except Exception:
        logger.exception("Animated welcome failed")
        await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(kb))

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_dev(uid):
        await update.message.reply_text("هذا الأمر متاح للمطور فقط.")
        return
    ok, data = await asyncio.to_thread(node_server_health)
    status = "متصل" if ok else "غير متصل"
    await update.message.reply_text(f"خادم Node: {status}\\nالرابط: {NODE_SERVER_URL}\\nالرد: {data}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """قائمة أوامر Qahtan:

/start - بدء البوت
/help - المساعدة
/chat - محادثة جديدة
/personality - تغيير الشخصية
/dialect - تغيير اللهجة
/mystats - إحصائياتك
/stats - إحصائيات البوت
/about - معلومات عن البوت

المطور: @rccjc (العراق)"""
    await update.message.reply_text(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - bot_start_time)
    text = f"""معلومات البوت:
الاسم: {BOT_NAME}
الإصدار: {BOT_VERSION}
نموذج الذكاء: {GROQ_MODEL}
المستخدمين: {len(bot_stats['users'])}
المسجات: {bot_stats['messages']}
وقت التشغيل: {fmt_uptime(uptime)}
المطور: @rccjc (العراق)"""
    await update.message.reply_text(text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - bot_start_time)
    text = f"""إحصائيات {BOT_NAME}:
المستخدمين: {len(bot_stats['users'])}
المسجات: {bot_stats['messages']}
الأخطاء: {bot_stats['errors']}
وقت التشغيل: {fmt_uptime(uptime)}"""
    await update.message.reply_text(text)

async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = []
    row = []
    for i, (key, name) in enumerate(PERS_AR.items()):
        row.append(InlineKeyboardButton(name, callback_data=f"pers_{key}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("رجوع", callback_data="cb_back")])
    
    await update.message.reply_text("*اختر شخصيتك المفضلة:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def dialect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = []
    row = []
    for i, (key, name) in enumerate(DIALECTS_AR.items()):
        row.append(InlineKeyboardButton(name, callback_data=f"dialect_{key}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("رجوع", callback_data="cb_back")])
    
    await update.message.reply_text("*اختر لهجتك:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stats = user_stats[uid]
    pers = PERS_AR.get(user_personality.get(uid, "normal"), "عادي")
    dialect = DIALECTS_AR.get(user_dialect.get(uid, "saudi"), "سعودي")
    msgs = user_message_count[uid]
    
    text = f"""إحصائياتك:
المسجات: {msgs}
الشخصية: {pers}
اللهجة: {dialect}"""
    await update.message.reply_text(text)

async def reset_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    conversation_history[uid].clear()
    await update.message.reply_text("تم مسح سجل المحادثة!")


def server_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 حالة السيرفر", callback_data="server_admin:status")],
        [InlineKeyboardButton("🟢 فحص Node", callback_data="server_admin:health")],
        [InlineKeyboardButton("📜 آخر السجلات", callback_data="server_admin:logs")],
        [InlineKeyboardButton("📁 ملفات المشروع", callback_data="server_admin:files")],
        [InlineKeyboardButton("⛔ إيقاف بعد تأكيد", callback_data="server_admin:stop")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cb_dev")],
    ])


def _read_recent_log_lines(limit: int = 30) -> str:
    candidates = ["bot.log", "logs/bot.log", "server.log"]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    return "".join(file.readlines()[-limit:])[-3500:]
            except OSError:
                pass
    return "لا يوجد ملف سجلات نصي؛ السجلات الحالية تظهر في سجل Workflow/المنصة."


def _server_snapshot() -> str:
    disk = shutil.disk_usage(os.getcwd())
    try:
        load = ", ".join(f"{value:.2f}" for value in os.getloadavg())
    except (AttributeError, OSError):
        load = "غير متاح"
    return (
        f"النظام: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
        f"المضيف: {socket.gethostname()}\n"
        f"Uptime البوت: {fmt_uptime(int(time.time() - bot_start_time))}\n"
        f"Load average: {load}\n"
        f"القرص المستخدم: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB\n"
        f"الرسائل: {bot_stats['messages']} | الأخطاء: {bot_stats['errors']}"
    )

# ============== معالجة الأزرار ==============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    
    try:
        if data == "cb_chat":
            await query.message.reply_text("اكتب رسالتك وسأرد عليك فوراً!")
            return
        elif data == "cb_music":
            music_search_mode.add(uid)
            await query.message.reply_text("اكتب اسم الاغنية للبحث:")
            return
        elif data == "cb_help":
            await query.message.reply_text("الأوامر: /start /help /chat /personality /dialect /mystats /stats /about")
            return
        elif data == "cb_about":
            uptime = int(time.time() - bot_start_time)
            await query.message.reply_text(f"{BOT_NAME} v{BOT_VERSION}\nAI: {GROQ_MODEL}\nUptime: {fmt_uptime(uptime)}\nالمطور: @rccjc")
            return
        elif data == "cb_back":
            kb = [
                [InlineKeyboardButton("محادثة ذكية", callback_data="cb_chat")],
                [InlineKeyboardButton("بحث اغاني", callback_data="cb_music")],
                [InlineKeyboardButton("ميزات إضافية", callback_data="feature:menu")],
                [InlineKeyboardButton("تغيير الشخصية", callback_data="cb_personality"), 
                 InlineKeyboardButton("تغيير اللهجة", callback_data="cb_dialect")],
                [InlineKeyboardButton("إحصائياتي", callback_data="cb_mystats"), 
                 InlineKeyboardButton("مساعدة", callback_data="cb_help")],
                [InlineKeyboardButton("لوحة المطور", callback_data="cb_dev")],
            ]
            await query.message.reply_text("اختر:", reply_markup=InlineKeyboardMarkup(kb))
            return
        elif data == "cb_dev":
            if uid in dev_mode_users:
                kb = [
                    [InlineKeyboardButton("إذاعة", callback_data="dev_broadcast"), InlineKeyboardButton("حظر", callback_data="dev_ban")],
                    [InlineKeyboardButton("إلغاء حظر", callback_data="dev_unban"), InlineKeyboardButton("إحصائيات", callback_data="dev_stats")],
                    [InlineKeyboardButton("المستخدمين", callback_data="dev_users"), InlineKeyboardButton("كود البوت", callback_data="dev_getcode")],
                    [InlineKeyboardButton("🖥️ تحكم بالسيرفر", callback_data="cb_server_admin")],
                    [InlineKeyboardButton("إيقاف البوت", callback_data="dev_shutdown"), InlineKeyboardButton("رجوع", callback_data="cb_back")],
                ]
                await query.message.reply_text("لوحة تحكم المطور", reply_markup=InlineKeyboardMarkup(kb))
            elif data == "cb_server_admin":
                if uid not in dev_mode_users:
                    await query.message.reply_text("هذه اللوحة تتطلب تفعيل وضع المطور بالرمز 505.")
                    return
                await query.message.reply_text("لوحة تحكم السيرفر الآمنة", reply_markup=server_admin_menu())
                return
            else:
                await query.message.reply_text("أدخل رمز المطور:")
                dev_pending_code[uid] = "dev_code"
    except Exception as e:
        logger.error(f"Callback error: {e}")
    
    if data.startswith("server_admin:"):
        if uid not in dev_mode_users:
            await query.message.reply_text("غير مصرح. فعّل وضع المطور بالرمز 505 أولًا.")
            return
        action = data.split(":", 1)[1]
        if action == "status":
            await query.message.reply_text("📊 حالة السيرفر:\n\n" + _server_snapshot(), reply_markup=server_admin_menu())
        elif action == "health":
            ok, payload = await asyncio.to_thread(node_server_health)
            state = "متصل" if ok else "غير متصل"
            await query.message.reply_text(f"🟢 Node: {state}\n{payload}", reply_markup=server_admin_menu())
        elif action == "logs":
            logs = _read_recent_log_lines()
            await query.message.reply_text("📜 آخر السجلات:\n\n" + logs[-3500:], reply_markup=server_admin_menu())
        elif action == "files":
            allowed = {"bot.py", "features.py", "utility_features.py", "run_all.py", "requirements.txt", "README_AR.md"}
            existing = sorted(name for name in allowed if os.path.isfile(name))
            await query.message.reply_text("📁 ملفات البوت المسموحة:\n" + "\n".join(existing), reply_markup=server_admin_menu())
        elif action == "stop":
            confirm = InlineKeyboardMarkup([
                [InlineKeyboardButton("تأكيد إيقاف البوت", callback_data="server_admin:confirm_stop")],
                [InlineKeyboardButton("إلغاء", callback_data="cb_server_admin")],
            ])
            await query.message.reply_text("هذا سيوقف عملية البوت الحالية. هل تؤكد؟", reply_markup=confirm)
        elif action == "confirm_stop":
            await query.message.reply_text("تم تأكيد الإيقاف.")
            os._exit(0)
        return

    if data == "cb_personality":
        kb = []
        row = []
        for i, (key, name) in enumerate(PERS_AR.items()):
            row.append(InlineKeyboardButton(name, callback_data=f"pers_{key}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("رجوع", callback_data="cb_back")])
        await query.message.reply_text("*اختر شخصيتك:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "cb_dialect":
        kb = []
        row = []
        for i, (key, name) in enumerate(DIALECTS_AR.items()):
            row.append(InlineKeyboardButton(name, callback_data=f"dialect_{key}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("رجوع", callback_data="cb_back")])
        await query.message.reply_text("*اختر لهجتك:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "cb_mystats":
        stats = user_stats[uid]
        pers = PERS_AR.get(user_personality.get(uid, "normal"), "عادي")
        dialect = DIALECTS_AR.get(user_dialect.get(uid, "saudi"), "سعودي")
        await query.message.reply_text(f"المسجات: {user_message_count[uid]}\nالشخصية: {pers}\nاللهجة: {dialect}")
    elif data.startswith("pers_"):
        key = data[5:]
        if key in PERSONALITIES:
            user_personality[uid] = key
            await query.message.reply_text(f"تم اختيار الشخصية: {PERS_AR.get(key)}")
    elif data.startswith("dialect_"):
        key = data[8:]
        if key in DIALECTS_AR:
            user_dialect[uid] = key
            await query.message.reply_text(f"تم اختيار اللهجة: {DIALECTS_AR.get(key)}")
    
    # ============== Music ==============
    elif data.startswith("music_"):
        index = int(data.split("_")[1])
        results = music_search_results.get(uid, [])
        
        if index >= len(results):
            await query.message.reply_text("حدث خطأ!")
            return
        
        result = results[index]
        await query.message.reply_text(f"جاري تحميل: {result['title']}...")
        
        # Try direct URL first
        audio_url = get_direct_audio_url(result["id"])
        
        if audio_url:
            try:
                await context.bot.send_voice(chat_id=uid, voice=audio_url, caption=result["title"][:200])
            except Exception as e:
                # Try download
                audio_file = download_audio(result["id"], f"audio_{uid}")
                if audio_file:
                    try:
                        with open(audio_file, "rb") as f:
                            await context.bot.send_voice(chat_id=uid, voice=f, caption=result["title"][:200])
                        import os
                        os.remove(audio_file)
                    except:
                        youtube_link = f"https://youtube.com/watch?v={result['id']}"
                        kb = [[InlineKeyboardButton("يوتيوب", url=youtube_link)]]
                        await query.message.reply_text("خطأ في الإرسال، خذ الرابط:", reply_markup=InlineKeyboardMarkup(kb))
                else:
                    youtube_link = f"https://youtube.com/watch?v={result['id']}"
                    kb = [[InlineKeyboardButton("يوتيوب", url=youtube_link)]]
                    await query.message.reply_text("ماقدر أحمل، خذ الرابط:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            youtube_link = f"https://youtube.com/watch?v={result['id']}"
            kb = [[InlineKeyboardButton("يوتيوب", url=youtube_link)]]
            await query.message.reply_text("ماقدر أجيب الصوت، خذ الرابط:", reply_markup=InlineKeyboardMarkup(kb))
        
        if uid in music_search_results:
            del music_search_results[uid]
        return
    
    # ============== أزرار المطور ==============
    elif data == "dev_broadcast":
        await query.message.reply_text("اكتب الرسالة التي تريد إذاعتها:")
        dev_pending_code[uid] = "broadcast"
    elif data == "dev_ban":
        await query.message.reply_text("أدخل معرف المستخدم لحظره:")
        dev_pending_code[uid] = "ban"
    elif data == "dev_unban":
        await query.message.reply_text("أدخل معرف المستخدم لإلغاء حظره:")
        dev_pending_code[uid] = "unban"
    elif data == "dev_stats":
        uptime = int(time.time() - bot_start_time)
        await query.message.reply_text(f"إحصائيات البوت:\nالمستخدمين: {len(bot_stats['users'])}\nالمسجات: {bot_stats['messages']}\nالأخطاء: {bot_stats['errors']}\nوقت التشغيل: {fmt_uptime(uptime)}")
    elif data == "dev_users":
        await query.message.reply_text(f"عدد المستخدمين: {len(bot_stats['users'])}\nالمستخدمين النشطون: {len([u for u in user_message_count if user_message_count[u] > 0])}")
    elif data == "dev_getcode":
        await query.message.reply_text("جاري إرسال كود البوت...")
        try:
            with open("bot.py", "rb") as f:
                await context.bot.send_document(chat_id=uid, document=f, caption="كود البوت - Qahtan v5.0.0\nالمطور: @rccjc")
        except Exception as e:
            await query.message.reply_text(f"خطأ في إرسال الملف: {str(e)}")
    elif data == "dev_shutdown":
        await query.message.reply_text("جاري إيقاف البوت...")
        import os
        os._exit(0)

# ============== معالجة الرسائل ==============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    msg = update.message.text.strip()
    uid = update.effective_user.id

    if await handle_feature_text(update, context):
        return
    
    if uid in banned_users:
        await update.message.reply_text("أنت محظور")
        return
    
    # Music search mode
    if uid in music_search_mode:
        music_search_mode.discard(uid)
        await handle_music_search(update, context)
        return
    
    # التحقق من كود المطور
    if uid in dev_pending_code:
        action = dev_pending_code.get(uid)
        
        # إذا كان ي Enter الكود أول مرة
        if action is True or action == "dev_code":
            if msg == DEVELOPER_MODE_CODE:
                dev_mode_users.add(uid)
                del dev_pending_code[uid]
                kb = [
                    [InlineKeyboardButton("إذاعة", callback_data="dev_broadcast"), InlineKeyboardButton("حظر", callback_data="dev_ban")],
                    [InlineKeyboardButton("إلغاء حظر", callback_data="dev_unban"), InlineKeyboardButton("إحصائيات", callback_data="dev_stats")],
                    [InlineKeyboardButton("المستخدمين", callback_data="dev_users"), InlineKeyboardButton("إيقاف", callback_data="dev_shutdown")],
                    [InlineKeyboardButton("رجوع", callback_data="cb_back")],
                ]
                await update.message.reply_text("تم تفعيل وضع المطور!", reply_markup=InlineKeyboardMarkup(kb))
                return
            else:
                del dev_pending_code[uid]
                await update.message.reply_text("رمز خاطئ!")
                return
            
        if action == "broadcast":
            # Send to all users
            count = 0
            for user_id in bot_stats["users"]:
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg)
                    count += 1
                except:
                    pass
            del dev_pending_code[uid]
            await update.message.reply_text(f"تم إرسال الرسالة إلى {count} مستخدم")
            return
            
        if action == "ban":
            try:
                banned_users.add(int(msg))
                del dev_pending_code[uid]
                await update.message.reply_text(f"تم حظر المستخدم {msg}")
            except:
                del dev_pending_code[uid]
                await update.message.reply_text("معرف غير صالح")
            return
            
        if action == "unban":
            try:
                banned_users.discard(int(msg))
                del dev_pending_code[uid]
                await update.message.reply_text(f"تم إلغاء حظر المستخدم {msg}")
            except:
                del dev_pending_code[uid]
                await update.message.reply_text("معرف غير صالح")
            return
        
        # Wrong code
        del dev_pending_code[uid]
        await update.message.reply_text("رمز خاطئ!")
        return
    
    # تحديث الإحصائيات
    bot_stats["users"].add(uid)
    bot_stats["messages"] += 1
    user_message_count[uid] += 1
    
    if is_rate_limited(uid):
        await update.message.reply_text("رجاءً انتظر قليلاً قبل إرسال رسالة أخرى")
        return
    
    # تجاهل الأوامر
    if msg.startswith("/"):
        return
    
    try:
        # إرسال typing
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # الحصول على الرد
        response = await get_ai_response(uid, msg)
        
        # إرسال الرد
        for part in split_msg(response):
            await update.message.reply_text(part)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        bot_stats["errors"] += 1
        await update.message.reply_text("عذراً، حدث خطأ. حاول لاحقاً.")

# ============== إعداد البوت ==============
async def post_init(app):
    commands = [
        BotCommand("start", "بدء البوت"),
        BotCommand("help", "المساعدة"),
        BotCommand("chat", "محادثة جديدة"),
        BotCommand("personality", "اختيار الشخصية"),
        BotCommand("dialect", "اختيار اللهجة"),
        BotCommand("mystats", "إحصائياتك"),
        BotCommand("stats", "إحصائيات البوت"),
        BotCommand("about", "معلومات"),
        BotCommand("dev", "وضع المطور"),
        BotCommand("server", "فحص خادم الاستضافة"),
        BotCommand("features", "الميزات الإضافية"),
        BotCommand("tiktok", "تحميل TikTok"),
        BotCommand("colorbuttons", "تلوين أزرار Python"),
        BotCommand("linkchannel", "ربط قناة"),
        BotCommand("channels", "قنواتي"),
        BotCommand("publish", "نشر في قناة"),
        BotCommand("featurestats", "إحصائيات الميزات"),
        BotCommand("commands", "قائمة الأوامر"),
        BotCommand("qr", "إنشاء QR"),
        BotCommand("checkurl", "فحص رابط"),
        BotCommand("remind", "إنشاء تذكير"),
        BotCommand("compress", "ضغط صورة"),
        BotCommand("id", "معرفات الحساب"),
        BotCommand("ping", "فحص السرعة"),
        BotCommand("privacy", "الخصوصية"),
    ]
    await app.bot.set_my_commands(commands)

def run_telegram_bot():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dev", dev_command))
    app.add_handler(CommandHandler("server", server_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("personality", personality_command))
    app.add_handler(CommandHandler("dialect", dialect_command))
    app.add_handler(CommandHandler("mystats", mystats_command))
    app.add_handler(CommandHandler("chat", reset_chat))
    app.add_handler(CommandHandler("reset", reset_chat))
    register_utility_handlers(app)
    register_feature_handlers(app)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info(f"{BOT_NAME} v{BOT_VERSION} شغال!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def main():
    validate_configuration()
    Thread(target=run_flask, daemon=True, name="flask-health").start()
    run_telegram_bot()


if __name__ == "__main__":
    main()
