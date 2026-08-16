"""Safe Telegram group administration for Az.

All mutating actions require a group/supergroup, the caller to be an admin,
and the bot to possess the relevant Telegram administrator right. Sensitive
operations are explicit commands and are never inferred from free-form AI text.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, ContextTypes

WARNINGS = defaultdict(lambda: defaultdict(int))


def _is_group(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in {"group", "supergroup"})


async def _caller_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not _is_group(update):
        await update.effective_message.reply_text("هذا الأمر يعمل داخل القروبات فقط.")
        return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
        await update.effective_message.reply_text("هذا الأمر للمشرفين فقط.")
        return False
    return True


async def _bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, right: str | None = None) -> bool:
    me = await context.bot.get_me()
    member = await context.bot.get_chat_member(update.effective_chat.id, me.id)
    if member.status == ChatMemberStatus.OWNER:
        return True
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        await update.effective_message.reply_text("ارفع البوت مشرفًا أولًا.")
        return False
    if right and not getattr(member, right, False):
        await update.effective_message.reply_text("صلاحية البوت المطلوبة غير مفعلة.")
        return False
    return True


def _target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.reply_to_message:
        return update.effective_message.reply_to_message.from_user
    if context.args and context.args[0].lstrip("-").isdigit():
        class UserRef:
            id = int(context.args[0])
            first_name = context.args[0]
            username = None
        return UserRef()
    return None


def _target_help() -> str:
    return "استخدم الأمر بالرد على رسالة العضو، أو اكتب المعرف بعد الأمر."


async def group_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "أوامر إدارة القروب:\n"
        "/gstatus حالة القروب\n/gadmins المشرفون\n/gid المعرفات\n"
        "/warn تحذير و /warnings الإنذارات\n/mute [دقائق] كتم\n/unmute فك الكتم\n"
        "/ban حظر و /unban فك الحظر\n/kick طرد\n/del حذف رسالة بالرد\n"
        "/pin تثبيت بالرد و /unpin إلغاء التثبيت\n/lock قفل الكتابة و /unlock فتحها\n"
        "/welcome تشغيل الترحيب أو /welcome off\n\n" + _target_help()
    )


async def group_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_group(update):
        await update.effective_message.reply_text("هذا الأمر يعمل داخل القروبات فقط.")
        return
    chat = await context.bot.get_chat(update.effective_chat.id)
    await update.effective_message.reply_text(
        f"اسم القروب: {chat.title}\nالمعرف: {chat.id}\nالنوع: {chat.type}\n"
        f"الوصف: {chat.description or 'لا يوجد'}"
    )


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_group(update):
        await update.effective_message.reply_text("هذا الأمر يعمل داخل القروبات فقط.")
        return
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    names = [f"{a.user.first_name} ({a.user.id})" for a in admins]
    await update.effective_message.reply_text("مشرفو القروب:\n" + "\n".join(names))


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text(_target_help())
        return
    if user.id == update.effective_user.id:
        await update.effective_message.reply_text("لا يمكنك تحذير نفسك.")
        return
    key = (update.effective_chat.id, user.id)
    WARNINGS[key[0]][key[1]] += 1
    count = WARNINGS[key[0]][key[1]]
    await update.effective_message.reply_text(f"تم تحذير {user.first_name}. عدد الإنذارات: {count}")
    if count >= 3:
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions=_no_permissions())
        await update.effective_message.reply_text("وصل العضو إلى ثلاثة إنذارات وتم كتمه.")


def _no_permissions():
    from telegram import ChatPermissions
    return ChatPermissions(can_send_messages=False)


def _all_permissions():
    from telegram import ChatPermissions
    return ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=False, can_invite_users=True, can_pin_messages=False)


async def warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_group(update):
        await update.effective_message.reply_text("هذا الأمر يعمل داخل القروبات فقط.")
        return
    user = _target(update, context) or update.effective_user
    count = WARNINGS[update.effective_chat.id][user.id]
    await update.effective_message.reply_text(f"إنذارات {user.first_name}: {count}")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text(_target_help())
        return
    minutes = 60
    for arg in context.args:
        if arg.isdigit():
            minutes = max(1, min(int(arg), 10080))
            break
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions=_no_permissions(), until_date=until)
    await update.effective_message.reply_text(f"تم كتم {user.first_name} لمدة {minutes} دقيقة.")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text(_target_help())
        return
    await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions=_all_permissions())
    await update.effective_message.reply_text(f"تم فك كتم {user.first_name}.")


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text(_target_help())
        return
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await update.effective_message.reply_text(f"تم حظر {user.first_name}.")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text("اكتب معرف العضو بعد الأمر.")
        return
    await context.bot.unban_chat_member(update.effective_chat.id, user.id, only_if_banned=True)
    await update.effective_message.reply_text(f"تم فك حظر العضو {user.id}.")


async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    user = _target(update, context)
    if not user:
        await update.effective_message.reply_text(_target_help())
        return
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await context.bot.unban_chat_member(update.effective_chat.id, user.id, only_if_banned=True)
    await update.effective_message.reply_text(f"تم طرد {user.first_name}.")


async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_delete_messages"):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("استخدم الأمر بالرد على الرسالة المراد حذفها.")
        return
    await context.bot.delete_message(update.effective_chat.id, update.effective_message.reply_to_message.message_id)
    await context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)


async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_pin_messages"):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("استخدم الأمر بالرد على الرسالة.")
        return
    await context.bot.pin_chat_message(update.effective_chat.id, update.effective_message.reply_to_message.message_id, disable_notification=True)
    await update.effective_message.reply_text("تم تثبيت الرسالة.")


async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_pin_messages"):
        return
    await context.bot.unpin_chat_message(update.effective_chat.id)
    await update.effective_message.reply_text("تم إلغاء تثبيت الرسالة.")


async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    await context.bot.set_chat_permissions(update.effective_chat.id, _no_permissions())
    await update.effective_message.reply_text("تم قفل الكتابة للأعضاء.")


async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _caller_admin(update, context) or not await _bot_admin(update, context, "can_restrict_members"):
        return
    await context.bot.set_chat_permissions(update.effective_chat.id, _all_permissions())
    await update.effective_message.reply_text("تم فتح الكتابة للأعضاء.")


def register_group_admin_handlers(application) -> None:
    commands = {
        "ghelp": group_help, "gstatus": group_status, "gadmins": list_admins,
        "warn": warn, "warnings": warnings, "mute": mute, "unmute": unmute,
        "ban": ban, "unban": unban, "kick": kick, "del": delete_message,
        "pin": pin, "unpin": unpin, "lock": lock, "unlock": unlock,
    }
    for name, handler in commands.items():
        application.add_handler(CommandHandler(name, handler))
