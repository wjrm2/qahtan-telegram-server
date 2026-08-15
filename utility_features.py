"""ميزات مساعدة مستقلة لبوت قحطان، بلا تنفيذ كود خارجي."""
from __future__ import annotations

import asyncio
import re
import time
from io import BytesIO
from urllib.parse import urlparse

import qrcode
import requests
from PIL import Image
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

MAX_REMINDER_SECONDS = 24 * 60 * 60
_reminders: dict[int, set[asyncio.Task]] = {}
_compress_waiting: set[int] = set()


def _parse_duration(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)\s*(s|m|h|d)", value.lower().strip())
    if not match:
        return None
    amount = int(match.group(1))
    factor = {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]
    seconds = amount * factor
    return seconds if 1 <= seconds <= MAX_REMINDER_SECONDS else None


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"معلوماتك:\nالمستخدم: {user.first_name}\nUser ID: `{user.id}`\nChat ID: `{chat.id}`",
        parse_mode="Markdown",
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    started = time.perf_counter()
    message = await update.message.reply_text("جاري القياس...")
    elapsed = round((time.perf_counter() - started) * 1000)
    await message.edit_text(f"Pong! سرعة استجابة Telegram تقريبًا: {elapsed}ms")


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "الأوامر الرئيسية:\n"
        "/start — القائمة الرئيسية\n"
        "/features — الميزات الإضافية\n"
        "/tiktok — تحميل TikTok\n"
        "/colorbuttons — تلوين أزرار Python\n"
        "/linkchannel — ربط قناة\n"
        "/channels — القنوات المربوطة\n"
        "/publish رقم | النص — نشر منشور\n"
        "/qr نص — إنشاء QR\n"
        "/checkurl رابط — فحص رابط\n"
        "/remind 10m النص — تذكير\n"
        "/compress — ضغط صورة\n"
        "/id — عرض المعرّفات\n"
        "/ping — فحص السرعة\n"
        "/reset — مسح المحادثة"
    )


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "الخصوصية:\n"
        "يُحفظ سجل المحادثة مؤقتًا أثناء تشغيل البوت لتحسين الردود. "
        "لا ترسل كلمات مرور أو رموز جلسات أو مفاتيح API. "
        "الملفات المرفوعة للمعالجة تُحذف بعد انتهاء المهمة."
    )


async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = " ".join(context.args).strip()
    if not value:
        await update.message.reply_text("الاستخدام: /qr النص أو الرابط")
        return
    if len(value) > 1000:
        await update.message.reply_text("النص طويل جدًا لإنشاء QR.")
        return
    image = qrcode.make(value).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    await update.message.reply_photo(photo=buffer, caption="تم إنشاء رمز QR.")


async def checkurl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = context.args[0].strip() if context.args else ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        await update.message.reply_text("أرسل رابطًا يبدأ بـ http:// أو https://")
        return
    try:
        started = time.perf_counter()
        response = await asyncio.to_thread(
            requests.get,
            url,
            headers={"User-Agent": "QahtanBot/5.1"},
            timeout=10,
            allow_redirects=True,
            stream=True,
        )
        elapsed = round((time.perf_counter() - started) * 1000)
        content_type = response.headers.get("content-type", "غير معروف").split(";", 1)[0]
        final_host = urlparse(response.url).netloc
        response.close()
        await update.message.reply_text(
            f"نتيجة فحص الرابط:\nالحالة: {response.status_code}\n"
            f"النطاق النهائي: {final_host}\nالنوع: {content_type}\nالزمن: {elapsed}ms"
        )
    except requests.RequestException:
        await update.message.reply_text("تعذر الوصول إلى الرابط أو انتهت المهلة.")


async def _reminder_task(bot, chat_id: int, seconds: int, text: str, task_holder: set) -> None:
    try:
        await asyncio.sleep(seconds)
        await bot.send_message(chat_id=chat_id, text=f"تذكيرك: {text}")
    except asyncio.CancelledError:
        return
    finally:
        task_holder.discard(asyncio.current_task())


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: /remind 10m النص")
        return
    seconds = _parse_duration(context.args[0])
    if seconds is None:
        await update.message.reply_text("استخدم مدة من 1s إلى 24h مثل 10m أو 2h.")
        return
    text = " ".join(context.args[1:]).strip()
    if len(text) > 500:
        await update.message.reply_text("نص التذكير طويل جدًا.")
        return
    tasks = _reminders.setdefault(update.effective_user.id, set())
    if len(tasks) >= 5:
        await update.message.reply_text("لديك 5 تذكيرات نشطة كحد أقصى.")
        return
    task = asyncio.create_task(_reminder_task(context.bot, update.effective_chat.id, seconds, text, tasks))
    tasks.add(task)
    await update.message.reply_text("تم إنشاء التذكير. سيعمل ما دام البوت متصلًا.")


async def cancel_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tasks = _reminders.pop(update.effective_user.id, set())
    for task in tasks:
        task.cancel()
    await update.message.reply_text(f"تم إلغاء {len(tasks)} تذكير.")


async def compress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _compress_waiting.add(update.effective_user.id)
    await update.message.reply_text("أرسل صورة، وسأضغطها بصيغة JPEG لتقليل حجمها.")


async def compress_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid not in _compress_waiting:
        return
    _compress_waiting.discard(uid)
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        raw = await file.download_as_bytearray()
        image = Image.open(BytesIO(raw)).convert("RGB")
        image.thumbnail((1920, 1920))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=82, optimize=True)
        buffer.seek(0)
        await update.message.reply_document(document=buffer, filename="qahtan-compressed.jpg", caption="تم ضغط الصورة.")
    except Exception:
        await update.message.reply_text("تعذر ضغط الصورة.")


def register_utility_handlers(application) -> None:
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("commands", commands_command))
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("qr", qr_command))
    application.add_handler(CommandHandler("checkurl", checkurl_command))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("cancelreminders", cancel_reminders_command))
    application.add_handler(CommandHandler("compress", compress_command))
    application.add_handler(MessageHandler(filters.PHOTO, compress_photo_handler))
