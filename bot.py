"""Qahtan bot core."""

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
import sys
import zipfile
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
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(PROJECT_ROOT, "bot.log")
from features import register_feature_handlers, handle_feature_text
from utility_features import register_utility_handlers
from service_catalog import catalog_categories, catalog_page, service_text, catalog_check_text, SERVICE_BY_KEY
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ============== الإعدادات ==============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
AI_PROVIDER = os.environ.get("AI_PROVIDER", "deepseek").strip().lower()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEVELOPER_IDS = {
    int(value.strip())
    for value in os.environ.get("DEVELOPER_IDS", "").split(",")
    if value.strip().isdigit()
}
BOT_NAME = "عز"
DEVELOPER_NAME = "فيصل العراقي"
DEVELOPER_USERNAME = "@rccjc"
BOT_VERSION = "5.5.0"
PORT = int(os.environ.get("BOT_PORT", os.environ.get("PORT", 8080)))
NODE_SERVER_PORT = int(os.environ.get("NODE_SERVER_PORT", 3000))
NODE_SERVER_URL = os.environ.get("NODE_SERVER_URL", f"http://127.0.0.1:{NODE_SERVER_PORT}").rstrip("/")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
ASSET_DIR = os.path.join(PROJECT_ROOT, "assets")
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
    "normal": "أنت عز، مساعد عراقي طبيعي وودود. رد باختصار وبوضوح وكأنك شخص حقيقي.",
    "funny": "أنت عز، مساعد عراقي خفيف الظل. كن طبيعيًا ومختصرًا، وعندما تضحك استخدم فقط: هههههههههههههههههههههههههههههههههه.",
    "serious": "أنت عز، مساعد عراقي جاد ومحترف. قدم جوابًا مختصرًا ودقيقًا.",
    "poet": "أنت عز، مساعد عراقي يكتب بأسلوب شعري عند الطلب، مع الاختصار.",
    "detective": "أنت عز، مساعد عراقي يحلل بهدوء ودقة وبردود مختصرة.",
    "teacher": "أنت عز، مساعد عراقي يشرح ببساطة وبأقصر جواب مفيد.",
    "philosopher": "أنت عز، مساعد عراقي يتأمل بوضوح دون إطالة.",
    "hacker": "أنت عز، مساعد تقني عراقي وأخلاقي. ساعد بأمان وباختصار.",
    "doctor": "أنت عز، مساعد يقدّم معلومات صحية عامة بحذر واختصار.",
    "chef": "أنت عز، مساعد طبخ عراقي يقدّم وصفات عملية ومختصرة.",
    "coach": "أنت عز، مساعد عراقي يقدم نصائح عملية ومباشرة.",
    "news": "أنت عز، مساعد يلخص الأخبار بوضوح مع التنبيه عند عدم التحقق.",
    "legal": "أنت عز، مساعد يشرح المعلومات القانونية العامة باختصار دون ادعاء أنه محام.",
    "tech": "أنت عز، مساعد تقني عراقي يعطي خطوات عملية ومختصرة.",
    "game": "أنت عز، مساعد ألعاب عراقي يتحدث طبيعيًا وباختصار.",
    "movies": "أنت عز، مساعد نقد سينمائي يجيب باختصار ووضوح.",
    "music": "أنت عز، مساعد موسيقى يتحدث طبيعيًا وباختصار.",
    "sports": "أنت عز، مساعد رياضي يلخص التحليل دون إطالة.",
    "islam": "أنت عز، مساعد يقدّم معلومات دينية بحذر وينبه إلى اختلاف الآراء.",
    "history": "أنت عز، مساعد تاريخي يذكر الحقائق باختصار.",
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
    return (
        f"{personality}\n"
        f"تحدث باللهجة {dialect_name}.\n"
        "اجعل الرد عادة بين جملة وثلاث جمل، ولا تستخدم الإيموجيات أو الزخرفة. "
        "لا تكرر السؤال ولا تبدأ موضوعًا جديدًا إذا كان المستخدم يتابع موضوعًا قائمًا. "
        "إذا كان الموقف مضحكًا فاستخدم: هههههههههههههههههههههههههههههههههه فقط.\n"
        "أنت عز، وكيل محادثي مستمر. حافظ على سياق المحادثة، "
        "حوّل الطلبات متعددة الخطوات إلى خطة، وتابع المهمة بعد كل رسالة. "
        "لا تدّعِ تنفيذ تكامل أو تشغيل سكربت ما لم تؤكده النتيجة. "
        "التكاملات تعرض متطلباتها قبل الربط، والعمليات الحساسة تحتاج تأكيدًا صريحًا. "
        "تشغيل Python يتم فقط داخل عزل محدود وليس على النظام المضيف.\n"
        "الكتالوج الحالي متاح من زر الخدمات، ويمكنك شرح متطلبات أي خدمة عند طلبها.\n"
        f"المطور: {DEVELOPER_NAME} ({DEVELOPER_USERNAME})"
    )

# ============== الذكاء الاصطناعي ==============
def ask_openai_compatible(url, api_key, model, messages):
    if not api_key:
        return ""
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "max_tokens": 900, "temperature": 0.6}
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        if response.ok:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        logger.error("AI provider error %s: %s", response.status_code, response.text[:300])
    except requests.RequestException as exc:
        logger.error("AI provider network error: %s", exc)
    except Exception:
        logger.exception("Unexpected AI provider error")
    return ""


def ask_deepseek(messages):
    return ask_openai_compatible(f"{DEEPSEEK_BASE_URL}/chat/completions", DEEPSEEK_API_KEY, DEEPSEEK_MODEL, messages)


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
        response = ""
        if AI_PROVIDER == "deepseek":
            response = await asyncio.to_thread(ask_deepseek, messages)
        if not response and GROQ_API_KEY:
            response = await asyncio.to_thread(ask_groq, messages)
        if not response:
            response = "لم يتم إعداد مزود الذكاء الاصطناعي بعد. أضف DEEPSEEK_API_KEY أو GROQ_API_KEY إلى البيئة."
        conversation_history[uid].extend([
            {"role": "user", "content": text},
            {"role": "assistant", "content": response},
        ])
        conversation_history[uid] = conversation_history[uid][-MAX_HISTORY * 2:]
        return response
    except Exception:
        logger.exception("AI response error")
        return "عذراً، حدث خطأ. حاول لاحقاً."

# ============== أوامر البوت ==============
async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in dev_mode_users:
        kb = [
            [InlineKeyboardButton("إذاعة", callback_data="dev_broadcast"), InlineKeyboardButton("حظر مستخدم", callback_data="dev_ban")],
            [InlineKeyboardButton("إلغاء الحظر", callback_data="dev_unban"), InlineKeyboardButton("إحصائيات شاملة", callback_data="dev_stats")],
            [InlineKeyboardButton("قائمة المستخدمين", callback_data="dev_users"), InlineKeyboardButton("تحميل الكود", callback_data="dev_getcode")],
            [InlineKeyboardButton("🖥️ تحكم بالسيرفر", callback_data="cb_server_admin")],
            [InlineKeyboardButton("إيقاف البوت", callback_data="dev_shutdown"), InlineKeyboardButton("رجوع", callback_data="cb_back")],
        ]
        await update.message.reply_text("لوحة تحكم المطور", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("أدخل رمز المطور:")
        dev_pending_code[uid] = "dev_code"

HEADER_IMAGE_PATH = os.path.join(ASSET_DIR, "qahtan_header.gif")


def main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 متابعة المحادثة", callback_data="cb_chat")],
        [InlineKeyboardButton("🔗 كتالوج الخدمات والمتطلبات", callback_data="svc_catalog")],
        [InlineKeyboardButton("🧩 الميزات", callback_data="feature:menu"), InlineKeyboardButton("🎵 بحث أغاني", callback_data="cb_music")],
        [InlineKeyboardButton("🧠 الشخصية", callback_data="cb_personality"), InlineKeyboardButton("🌐 اللهجة", callback_data="cb_dialect")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="cb_mystats"), InlineKeyboardButton("❔ المساعدة", callback_data="cb_help")],
        [InlineKeyboardButton("🛠️ لوحة المطور", callback_data="dev_panel")],
    ])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_stats[uid]["start_time"] = time.time()
    caption = (
        "عز جاهز. اكتب طلبك مباشرة، وسأتابع سياق المحادثة وأوضح المتطلبات قبل أي ربط أو تنفيذ.\n\n"
        "اختر خدمة من الكتالوج لعرض حالتها ومتطلبات تفعيلها."
    )
    if os.path.exists(HEADER_IMAGE_PATH):
        try:
            with open(HEADER_IMAGE_PATH, "rb") as image:
                await update.message.reply_animation(animation=image, caption=caption, reply_markup=main_menu_markup())
            return
        except Exception:
            logger.exception("Header image failed")
    await update.message.reply_text(caption, reply_markup=main_menu_markup())

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_dev(uid):
        await update.message.reply_text("هذا الأمر متاح للمطور فقط.")
        return
    ok, data = await asyncio.to_thread(node_server_health)
    status = "متصل" if ok else "غير متصل"
    await update.message.reply_text(f"خادم Node: {status}\\nالرابط: {NODE_SERVER_URL}\\nالرد: {data}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """قائمة أوامر عز:

/start - بدء البوت
/help - المساعدة
/chat - محادثة جديدة
/personality - تغيير الشخصية
/dialect - تغيير اللهجة
/mystats - إحصائياتك
/stats - إحصائيات البوت
/about - معلومات عن البوت

المطور: فيصل العراقي
للمساعدة: @rccjc"""
    await update.message.reply_text(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - bot_start_time)
    text = f"""معلومات البوت:
الاسم: {BOT_NAME}
الإصدار: {BOT_VERSION}
نموذج الذكاء: {AI_PROVIDER}/{DEEPSEEK_MODEL if AI_PROVIDER == 'deepseek' else GROQ_MODEL}
المستخدمين: {len(bot_stats['users'])}
المسجات: {bot_stats['messages']}
وقت التشغيل: {fmt_uptime(uptime)}
المطور: فيصل العراقي
للمساعدة: @rccjc"""
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
        [InlineKeyboardButton("🖥️ كمبيوتر آمن", callback_data="server_admin:computer")],
        [InlineKeyboardButton("⛔ إيقاف بعد تأكيد", callback_data="server_admin:stop")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cb_dev")],
    ])


PROJECT_ARCHIVE_FILES = (
    "bot.py",
    "features.py",
    "utility_features.py",
    "run_all.py",
    "requirements.txt",
    "README_AR.md",
    ".env.example",
    ".github/workflows/run-bot.yml",
    "node_server/server.ts",
    "node_server/package.json",
    "node_server/package-lock.json",
    "assets/qahtan_menu.gif",
    "assets/qahtan_header.gif",
    "service_catalog.py",
)


def _build_project_archive() -> BytesIO:
    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in PROJECT_ARCHIVE_FILES:
            absolute_path = os.path.join(PROJECT_ROOT, relative_path)
            if os.path.isfile(absolute_path):
                archive.write(absolute_path, arcname=relative_path)
    archive_buffer.seek(0)
    return archive_buffer


def _read_recent_log_lines(limit: int = 30) -> str:
    candidates = [LOG_PATH, os.path.join(PROJECT_ROOT, "logs", "bot.log"), os.path.join(PROJECT_ROOT, "server.log")]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    return "".join(file.readlines()[-limit:])[-3500:]
            except OSError:
                pass
    return "لا يوجد ملف سجلات نصي؛ السجلات الحالية تظهر في سجل Workflow/المنصة."


def computer_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐍 معلومات Python", callback_data="computer:python")],
        [InlineKeyboardButton("🐧 معلومات Linux", callback_data="computer:linux")],
        [InlineKeyboardButton("📁 ملفات المشروع المسموحة", callback_data="computer:files")],
        [InlineKeyboardButton("🩺 تشخيص آمن", callback_data="computer:diagnostics")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cb_server_admin")],
    ])


def _server_snapshot() -> str:
    disk = shutil.disk_usage(PROJECT_ROOT)
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
        if data == "svc_catalog":
            await query.edit_message_text("🔗 كتالوج الخدمات\nاختر تصنيفًا لعرض الخدمات ومتطلبات الربط:", reply_markup=catalog_categories())
            return
        elif data == "svc_check":
            await query.edit_message_text(catalog_check_text(), reply_markup=catalog_categories())
            return
        elif data.startswith("svc_cat:"):
            category = data.split(":", 1)[1]
            await query.edit_message_text(f"🔗 {category}\nاختر خدمة لعرض المتطلبات:", reply_markup=catalog_page(0, category))
            return
        elif data.startswith("svc_page:"):
            parts = data.split(":", 2)
            page = int(parts[1])
            category = parts[2] if len(parts) > 2 else None
            await query.edit_message_text("🔗 الخدمات\nاختر خدمة لعرض المتطلبات:", reply_markup=catalog_page(page, category))
            return
        elif data.startswith("svc:"):
            service = SERVICE_BY_KEY.get(data.split(":", 1)[1])
            if not service:
                await query.edit_message_text("الخدمة غير موجودة في الكتالوج.", reply_markup=catalog_categories())
            else:
                await query.edit_message_text(service_text(service), parse_mode="HTML", reply_markup=catalog_page(0, service.category))
            return
        if data == "cb_chat":
            await query.message.reply_text("أرسل رسالتك أو تابع آخر مهمة؛ سأحافظ على سياق المحادثة السابقة.")

            return
        elif data == "cb_music":
            music_search_mode.add(uid)
            await query.message.reply_text("اكتب اسم الاغنية للبحث:")
            return
        elif data == "cb_help":
            await query.message.reply_text("الأوامر: /start /help /chat /personality /dialect /mystats /stats /about\nللمساعدة: @rccjc")
            return
        elif data == "cb_about":
            uptime = int(time.time() - bot_start_time)
            await query.message.reply_text(f"{BOT_NAME} v{BOT_VERSION}\nAI: {AI_PROVIDER}/{DEEPSEEK_MODEL if AI_PROVIDER == 'deepseek' else GROQ_MODEL}\nUptime: {fmt_uptime(uptime)}\nالمطور: فيصل العراقي - @rccjc")
            return
        elif data == "cb_back":
            await query.message.reply_text("لوحة عز الرئيسية:", reply_markup=main_menu_markup())
            return
        elif data in {"cb_dev", "dev_panel"}:
            if uid in dev_mode_users:
                kb = [
                    [InlineKeyboardButton("إذاعة", callback_data="dev_broadcast"), InlineKeyboardButton("حظر", callback_data="dev_ban")],
                    [InlineKeyboardButton("إلغاء حظر", callback_data="dev_unban"), InlineKeyboardButton("إحصائيات", callback_data="dev_stats")],
                    [InlineKeyboardButton("المستخدمين", callback_data="dev_users"), InlineKeyboardButton("كود البوت", callback_data="dev_getcode")],
                    [InlineKeyboardButton("🖥️ تحكم بالسيرفر", callback_data="cb_server_admin")],
                    [InlineKeyboardButton("إيقاف البوت", callback_data="dev_shutdown"), InlineKeyboardButton("رجوع", callback_data="cb_back")],
                ]
                await query.message.reply_text("لوحة تحكم المطور", reply_markup=InlineKeyboardMarkup(kb))
            else:
                await query.message.reply_text("أدخل رمز المطور:")
                dev_pending_code[uid] = "dev_code"
            return
        elif data == "cb_server_admin":
            if uid not in dev_mode_users:
                await query.message.reply_text("هذه اللوحة تتطلب تفعيل وضع المطور بالرمز 505.")
                return
            await query.message.reply_text("لوحة تحكم السيرفر الآمنة", reply_markup=server_admin_menu())
            return
    except Exception as e:
        logger.error(f"Callback error: {e}")
    
    if data.startswith("server_admin:"):
        if uid not in dev_mode_users:
            await query.message.reply_text("غير مصرح. فعّل وضع المطور بالرمز 505 أولًا.")
            return
        action = data.split(":", 1)[1]
        if action == "status":
            try:
                snapshot = _server_snapshot()
                await query.message.reply_text("📊 حالة السيرفر:\n\n" + snapshot, reply_markup=server_admin_menu())
            except Exception:
                logger.exception("Server status callback failed")
                await query.message.reply_text("تعذر قراءة حالة السيرفر حاليًا.", reply_markup=server_admin_menu())
        elif action == "health":
            ok, payload = await asyncio.to_thread(node_server_health)
            state = "متصل" if ok else "غير متصل"
            await query.message.reply_text(f"🟢 Node: {state}\\n{payload}", reply_markup=server_admin_menu())
        elif action == "computer":
            await query.message.reply_text("🖥️ كمبيوتر آمن\\nلا يوجد ترمنال مفتوح؛ اختر فحصًا محددًا:", reply_markup=computer_menu())
        elif action == "logs":
            logs = _read_recent_log_lines()
            await query.message.reply_text("📜 آخر السجلات:\n\n" + logs[-3500:], reply_markup=server_admin_menu())
        elif action == "files":
            try:
                existing = [
                    relative_path for relative_path in PROJECT_ARCHIVE_FILES
                    if os.path.isfile(os.path.join(PROJECT_ROOT, relative_path))
                ]
                archive_buffer = _build_project_archive()
                await query.message.reply_document(
                    document=InputFile(archive_buffer, filename="qahtan-project-safe.zip"),
                    caption="حزمة المشروع بدون .env أو المفاتيح أو node_modules أو السجلات.\n\nالملفات: " + ", ".join(existing),
                    reply_markup=server_admin_menu(),
                )
            except Exception:
                logger.exception("Project archive callback failed")
                await query.message.reply_text("تعذر تجهيز ملف المشروع حاليًا.", reply_markup=server_admin_menu())
        elif action == "stop":
            confirm = InlineKeyboardMarkup([
                [InlineKeyboardButton("تأكيد إيقاف البوت", callback_data="server_admin:confirm_stop")],
                [InlineKeyboardButton("إلغاء", callback_data="cb_server_admin")],
            ])
            await query.message.reply_text("هذا سيوقف عملية البوت الحالية. هل تؤكد؟", reply_markup=confirm)
        elif action == "confirm_stop":
            await query.message.reply_text("تم تأكيد الإيقاف.")
            os._exit(0)
    if data.startswith("computer:"):
        if uid not in dev_mode_users:
            await query.message.reply_text("غير مصرح. فعّل وضع المطور بالرمز 505 أولًا.")
            return
        action = data.split(":", 1)[1]
        if action == "python":
            await query.message.reply_text(
                f"🐍 Python\\nالإصدار: {platform.python_version()}\\nالمفسر: {sys.executable}\\nالمشروع: {PROJECT_ROOT}",
                reply_markup=computer_menu(),
            )
        elif action == "linux":
            await query.message.reply_text(
                f"🐧 Linux\\nالنظام: {platform.system()} {platform.release()}\\nالمضيف: {socket.gethostname()}\\nالمعمارية: {platform.machine()}",
                reply_markup=computer_menu(),
            )
        elif action == "files":
            existing = [
                relative_path for relative_path in PROJECT_ARCHIVE_FILES
                if os.path.isfile(os.path.join(PROJECT_ROOT, relative_path))
            ]
            archive_buffer = _build_project_archive()
            await query.message.reply_text(
                "📁 الملفات المتاحة وإرسال الحزمة:\\n" + "\\n".join(existing),
                reply_markup=computer_menu(),
            )
            await query.message.reply_document(
                document=InputFile(archive_buffer, filename="qahtan-project-safe.zip"),
                caption="حزمة آمنة بدون الأسرار أو ملفات التشغيل المؤقتة.",
            )
        elif action == "diagnostics":
            disk = shutil.disk_usage(PROJECT_ROOT)
            await query.message.reply_text(
                f"🩺 التشخيص الآمن\\nالقرص المتاح: {disk.free // (1024**3)}GB\\n"
                f"الذاكرة التقريبية: {getattr(__import__('os'), 'getloadavg', lambda: ('غير متاح',))()}",
                reply_markup=computer_menu(),
            )
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
                await context.bot.send_document(chat_id=uid, document=f, caption="كود البوت - Qahtan v5.0.0\nالمطور: فيصل العراقي - @rccjc")
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
                    [InlineKeyboardButton("🖥️ تحكم بالسيرفر", callback_data="cb_server_admin")],
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
