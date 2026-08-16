"""ميزات إضافية آمنة لبوت قحطان.

لا ينفذ هذا الملف أي كود يرفعه المستخدم، ولا يتعامل مع sessionid أو عمليات
تعديل/حذف جماعية في حسابات TikTok. يقتصر على تنزيل الروابط العامة، وتحويل
ملفات Python نصيًا، وربط القنوات التي يملك المستخدم صلاحية إدارتها.
"""
from __future__ import annotations

import ast
import asyncio
import html
import logging
import os
import re
import sqlite3
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)
DATA_DIR = Path(os.getenv("FEATURE_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("FEATURE_DB_PATH", str(DATA_DIR / "features.sqlite3")))
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_DOWNLOAD_MB", "50")) * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024

_state_lock = threading.Lock()
_feature_state: dict[int, str] = {}
_feature_data: dict[int, dict[str, Any]] = {}
_db_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_feature_db() -> None:
    with _db_lock, _conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS feature_users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS feature_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                username TEXT,
                link TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_user_id, channel_id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS feature_stats (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        db.commit()


def _ensure_user(user) -> None:
    with _db_lock, _conn() as db:
        db.execute(
            "INSERT OR IGNORE INTO feature_users(telegram_id, username, full_name) VALUES (?, ?, ?)",
            (user.id, user.username or "", user.full_name or ""),
        )
        db.execute(
            "UPDATE feature_users SET username=?, full_name=? WHERE telegram_id=?",
            (user.username or "", user.full_name or "", user.id),
        )
        db.commit()


def _inc_stat(key: str) -> None:
    with _db_lock, _conn() as db:
        db.execute(
            "INSERT INTO feature_stats(key, value) VALUES (?, 1) "
            "ON CONFLICT(key) DO UPDATE SET value=value+1",
            (key,),
        )
        db.commit()


def _set_state(user_id: int, state: str | None, **data: Any) -> None:
    with _state_lock:
        if state is None:
            _feature_state.pop(user_id, None)
            _feature_data.pop(user_id, None)
        else:
            _feature_state[user_id] = state
            _feature_data.setdefault(user_id, {}).update(data)


def _get_state(user_id: int) -> tuple[str | None, dict[str, Any]]:
    with _state_lock:
        return _feature_state.get(user_id), dict(_feature_data.get(user_id, {}))


def _user_channels(user_id: int):
    with _db_lock, _conn() as db:
        return db.execute(
            "SELECT * FROM feature_channels WHERE telegram_user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()


def _channel_for_user(channel_db_id: int, user_id: int):
    with _db_lock, _conn() as db:
        return db.execute(
            "SELECT * FROM feature_channels WHERE id=? AND telegram_user_id=?",
            (channel_db_id, user_id),
        ).fetchone()


def _is_public_tiktok_url(value: str) -> bool:
    try:
        host = (urlparse(value.strip()).hostname or "").lower()
        return host == "tiktok.com" or host.endswith(".tiktok.com")
    except ValueError:
        return False


def _download_tiktok(url: str) -> str | None:
    token = uuid.uuid4().hex
    temp_dir = Path(tempfile.mkdtemp(prefix="qahtan-tiktok-"))
    output = temp_dir / f"{token}.%(ext)s"
    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "format": "mp4/best[ext=mp4]/best",
        "outtmpl": str(output),
        "max_filesize": MAX_DOWNLOAD_BYTES,
        "socket_timeout": 20,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = Path(ydl.prepare_filename(info))
            if not filename.exists():
                candidates = list(temp_dir.glob("*") )
                filename = candidates[0] if candidates else filename
            if not filename.exists() or filename.stat().st_size > MAX_DOWNLOAD_BYTES:
                return None
            return str(filename)
    except Exception:
        logger.exception("TikTok download failed")
        return None
    finally:
        # The caller removes the successful file; failed/empty directories are cleaned here.
        for candidate in temp_dir.glob("*"):
            if not candidate.exists():
                continue
            if candidate.suffix == ".part" or candidate.stat().st_size == 0:
                candidate.unlink(missing_ok=True)
        try:
            if not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except OSError:
            pass


class _ButtonCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[ast.Call] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name == "InlineKeyboardButton":
            self.calls.append(node)
        self.generic_visit(node)


def colorize_python_source(source: str, style: str) -> tuple[str, int]:
    """Add a Telegram button style to simple one-line button calls, without executing code."""
    if style not in {"primary", "success", "danger"}:
        raise ValueError("unsupported style")
    tree = ast.parse(source)
    visitor = _ButtonCallVisitor()
    visitor.visit(tree)
    lines = source.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    changed = 0
    for node in visitor.calls:
        if any(keyword.arg == "style" for keyword in node.keywords):
            continue
        if node.lineno != node.end_lineno:
            continue
        line_index = node.lineno - 1
        line = lines[line_index]
        # إحداثيات AST قد تكون محسوبة بالبايت مع Unicode؛ نستخدم آخر قوس في السطر.
        close_index = line.rfind(")")
        if close_index <= 0:
            continue
        edits.append((line_index, close_index, f', style="{style}"'))
    for line_index, close_index, addition in sorted(edits, reverse=True):
        lines[line_index] = lines[line_index][:close_index] + addition + lines[line_index][close_index:]
        changed += 1
    return "".join(lines), changed


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 تحميل TikTok", callback_data="feature:tiktok")],
        [InlineKeyboardButton("🎨 تلوين أزرار Python", callback_data="feature:color")],
        [InlineKeyboardButton("📢 ربط ونشر في القنوات", callback_data="feature:channels")],
        [InlineKeyboardButton("📊 إحصائيات الميزات", callback_data="feature:stats")],
    ])


async def features_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_user(update.effective_user)
    await update.message.reply_text("اختر ميزة:", reply_markup=_main_menu())


async def tiktok_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _set_state(update.effective_user.id, "tiktok_url")
    await update.message.reply_text("أرسل رابط TikTok عام لتحميله. الحد الأقصى 50MB.")


async def color_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _set_state(update.effective_user.id, "color_file")
    await update.message.reply_text("أرسل ملف Python بصيغة .py، وسأضيف نمطًا للأزرار دون تشغيل الملف.")


async def link_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _set_state(update.effective_user.id, "channel_link")
    await update.message.reply_text("أضف البوت مشرفًا في القناة، ثم أرسل @username القناة أو رابط t.me العام.")


async def channel_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args).strip()
    if not raw:
        await update.message.reply_text("الاستخدام: /channelinfo @username أو رابط القناة")
        return
    target = raw.split()[0]
    if target.startswith("https://t.me/"):
        target = "@" + target.rstrip("/").rsplit("/", 1)[-1]
    elif not target.startswith("@"):
        target = "@" + target
    try:
        chat = await context.bot.get_chat(target)
        count = await context.bot.get_chat_member_count(chat.id)
        me = await context.bot.get_me()
        bot_member = await context.bot.get_chat_member(chat.id, me.id)
        admins = {"administrator", "creator"}
        bot_rights = {}
        if bot_member.status in admins:
            for key in ("can_post_messages", "can_edit_messages", "can_delete_messages", "can_restrict_members", "can_promote_members", "can_invite_users", "can_pin_messages"):
                bot_rights[key] = bool(getattr(bot_member, key, False))
        username = getattr(chat, "username", None)
        link = f"https://t.me/{username}" if username else "لا يوجد رابط عام"
        await update.message.reply_text(
            f"بيانات القناة المؤكدة:\nالاسم: {chat.title or 'بدون اسم'}\n"
            f"المعرف: {chat.id}\nالرابط: {link}\nعدد الأعضاء: {count}\n"
            f"حالة البوت: {bot_member.status}\nالصلاحيات: {bot_rights or 'غير مشرف'}"
        )
    except Exception as exc:
        logger.exception("Channel info failed")
        await update.message.reply_text(f"تعذر التحقق من القناة عبر Telegram: {exc}")


async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channels = _user_channels(update.effective_user.id)
    if not channels:
        await update.message.reply_text("لا توجد قنوات مربوطة. استخدم /linkchannel أولًا.")
        return
    text = "قنواتك المربوطة:\n\n" + "\n".join(
        f"#{row['id']} — {row['title']} — {row['link'] or 'بدون رابط'}" for row in channels
    )
    await update.message.reply_text(text)


async def publish_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args).strip()
    if "|" not in raw:
        await update.message.reply_text("الاستخدام: /publish رقم_القناة_من_channels | نص المنشور")
        return
    channel_id_text, text = [part.strip() for part in raw.split("|", 1)]
    try:
        channel_db_id = int(channel_id_text)
    except ValueError:
        await update.message.reply_text("رقم القناة غير صحيح. استخدم /channels لمعرفة الأرقام.")
        return
    channel = _channel_for_user(channel_db_id, update.effective_user.id)
    if not channel:
        await update.message.reply_text("القناة غير موجودة أو ليست مربوطة بحسابك.")
        return
    if not text:
        await update.message.reply_text("نص المنشور فارغ.")
        return
    try:
        await context.bot.send_message(chat_id=channel["channel_id"], text=text)
        _inc_stat("published_posts")
        await update.message.reply_text(f"تم نشر المنشور في {channel['title']}.")
    except Exception:
        logger.exception("Channel publish failed")
        await update.message.reply_text("تعذر النشر. تأكد من أن البوت مشرف ولديه صلاحية النشر.")


async def feature_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with _db_lock, _conn() as db:
        users = db.execute("SELECT COUNT(*) AS n FROM feature_users").fetchone()["n"]
        channels = db.execute("SELECT COUNT(*) AS n FROM feature_channels").fetchone()["n"]
        stats = {row["key"]: row["value"] for row in db.execute("SELECT key,value FROM feature_stats")}
    await update.message.reply_text(
        "إحصائيات الميزات:\n"
        f"المستخدمون: {users}\nالقنوات: {channels}\n"
        f"تحميلات TikTok: {stats.get('tiktok_downloads', 0)}\n"
        f"ملفات الأزرار: {stats.get('colored_files', 0)}\n"
        f"المنشورات: {stats.get('published_posts', 0)}"
    )


async def _handle_tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    notice = await update.message.reply_text("جاري تجهيز الفيديو...")
    path = await asyncio.to_thread(_download_tiktok, url)
    if not path:
        await notice.edit_text("تعذر تحميل الرابط أو أن حجمه أكبر من الحد المسموح.")
        return
    try:
        with open(path, "rb") as video:
            await update.message.reply_video(video=video, caption="تم التحميل بواسطة قحطان")
        _inc_stat("tiktok_downloads")
        await notice.delete()
    except Exception:
        logger.exception("Sending TikTok video failed")
        await notice.edit_text("تم التحميل لكن تعذر إرسال الفيديو إلى Telegram.")
    finally:
        try:
            Path(path).unlink(missing_ok=True)
            parent = Path(path).parent
            if not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass


async def _handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = (update.message.text or "").strip()
    match = re.match(r"^(?:https?://t\.me/)?@?([A-Za-z0-9_]{5,32})/?$", raw)
    if not match:
        await update.message.reply_text("أرسل @username صحيحًا لقناة عامة.")
        return
    username = match.group(1)
    try:
        chat = await context.bot.get_chat(f"@{username}")
        member_count = await context.bot.get_chat_member_count(chat.id)
        me = await context.bot.get_me()
        bot_member = await context.bot.get_chat_member(chat.id, me.id)
        user_member = await context.bot.get_chat_member(chat.id, update.effective_user.id)
        if bot_member.status not in {"administrator", "creator"}:
            await update.message.reply_text("يجب أن يكون البوت مشرفًا في القناة.")
            return
        if user_member.status not in {"administrator", "creator"}:
            await update.message.reply_text("يجب أن تكون مشرفًا أو مالكًا للقناة.")
            return
        _ensure_user(update.effective_user)
        with _db_lock, _conn() as db:
            db.execute(
                "INSERT OR IGNORE INTO feature_channels(telegram_user_id,channel_id,title,username,link) VALUES (?,?,?,?,?)",
                (update.effective_user.id, chat.id, chat.title or username, username, f"https://t.me/{username}"),
            )
            db.commit()
        _set_state(update.effective_user.id, None)
        await update.message.reply_text(f"تم ربط القناة بنجاح. عدد الأعضاء المؤكد الآن: {member_count}. استخدم /channelinfo @{username} للتحقق لاحقًا.")
    except Exception:
        logger.exception("Channel link failed")
        await update.message.reply_text("تعذر ربط القناة. تأكد من أنها عامة وأن البوت مضاف كمشرف.")


async def handle_feature_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    uid = update.effective_user.id
    state, _ = _get_state(uid)
    if state == "tiktok_url":
        url = (update.message.text or "").strip()
        if not _is_public_tiktok_url(url):
            await update.message.reply_text("أرسل رابط TikTok عام صحيح.")
            return True
        _set_state(uid, None)
        await _handle_tiktok(update, context, url)
        return True
    if state == "channel_link":
        await _handle_channel_link(update, context)
        return True
    if "tiktok.com" in (update.message.text or ""):
        await _handle_tiktok(update, context, update.message.text.strip())
        return True
    return False


async def _handle_color_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    state, _ = _get_state(uid)
    if state != "color_file":
        return
    document = update.message.document
    if not document.file_name or not document.file_name.lower().endswith(".py"):
        await update.message.reply_text("أرسل ملف Python بامتداد .py فقط.")
        return
    if document.file_size and document.file_size > MAX_SOURCE_BYTES:
        await update.message.reply_text("الملف أكبر من الحد المسموح 2MB.")
        return
    temp_path = Path(tempfile.gettempdir()) / f"qahtan-{uuid.uuid4().hex}.py"
    try:
        tg_file = await context.bot.get_file(document.file_id)
        await tg_file.download_to_drive(custom_path=str(temp_path))
        source = temp_path.read_text(encoding="utf-8", errors="ignore")
        style = "success"
        transformed, changed = colorize_python_source(source, style)
        if not changed:
            await update.message.reply_text("لم أجد أزرار InlineKeyboardButton قابلة للتعديل.")
            return
        output_path = temp_path.with_name(f"colored_{document.file_name}")
        output_path.write_text(transformed, encoding="utf-8")
        with open(output_path, "rb") as output:
            await update.message.reply_document(document=output, caption=f"تم تعديل {changed} زر دون تشغيل الملف.")
        _inc_stat("colored_files")
    except (SyntaxError, UnicodeError):
        await update.message.reply_text("تعذر تحليل ملف Python.")
    except Exception:
        logger.exception("Button coloring failed")
        await update.message.reply_text("حدث خطأ أثناء معالجة الملف.")
    finally:
        _set_state(uid, None)
        temp_path.unlink(missing_ok=True)
        temp_path.with_name(f"colored_{document.file_name}").unlink(missing_ok=True)


async def feature_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "feature:menu":
        await query.message.reply_text("اختر ميزة:", reply_markup=_main_menu())
    elif query.data == "feature:tiktok":
        _set_state(query.from_user.id, "tiktok_url")
        await query.message.reply_text("أرسل رابط TikTok العام.")
    elif query.data == "feature:color":
        _set_state(query.from_user.id, "color_file")
        await query.message.reply_text("أرسل ملف Python بصيغة .py لتلوين أزراره.")
    elif query.data == "feature:channels":
        await query.message.reply_text("الأوامر: /linkchannel ثم /channels ثم /publish رقم | نص")
    elif query.data == "feature:stats":
        await feature_stats_command(update, context)


def register_feature_handlers(application) -> None:
    init_feature_db()
    application.add_handler(CommandHandler("features", features_command))
    application.add_handler(CommandHandler("tiktok", tiktok_command))
    application.add_handler(CommandHandler("colorbuttons", color_command))
    application.add_handler(CommandHandler("linkchannel", link_channel_command))
    application.add_handler(CommandHandler("channels", channels_command))
    application.add_handler(CommandHandler("channelinfo", channel_info_command))
    application.add_handler(CommandHandler("publish", publish_command))
    application.add_handler(CommandHandler("featurestats", feature_stats_command))
    application.add_handler(CallbackQueryHandler(feature_callback, pattern=r"^feature:"))
    application.add_handler(MessageHandler(filters.Document.ALL, _handle_color_document))
