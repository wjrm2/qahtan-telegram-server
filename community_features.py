"""Community moderation, protection, and game feature catalog for Az.

The module contains original metadata and UI only. It does not copy code from
third-party repositories and never claims that an external credential exists.
Sensitive moderation actions must still pass the existing Telegram permission
checks before a real executor is connected.
"""
from __future__ import annotations

from dataclasses import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes


@dataclass(frozen=True)
class CommunityFeature:
    key: str
    title: str
    category: str
    kind: str
    requirement: str
    status: str = "بطاقة متطلبات؛ يحتاج ربط المنفذ"


_RAW = {
    "إدارة القروبات": [
        ("قواعد المجموعة", "إدارة", "صلاحية إرسال وتعديل رسالة القواعد"),
        ("رسالة ترحيب ذكية", "إدارة", "قالب ورسالة ترحيب، مع حذف اختياري"),
        ("رسالة وداع", "إدارة", "صلاحية حذف الرسائل الاختيارية"),
        ("استقبال الأعضاء الجدد", "إدارة", "صلاحية قراءة أحداث الانضمام"),
        ("قائمة المشرفين", "إدارة", "صلاحية قراءة أعضاء المجموعة"),
        ("تدقيق صلاحيات البوت", "إدارة", "البوت مشرف حتى تظهر الصلاحيات الفعلية"),
        ("رفع مشرف بنمط محدد", "إدارة", "صلاحية ترقية الأعضاء وموافقة الصانع"),
        ("تنزيل مشرف بنمط محدد", "إدارة", "صلاحية خفض المشرفين وموافقة الصانع"),
        ("حظر عضو مؤقت", "إدارة", "صلاحية حظر الأعضاء ومدة محددة"),
        ("فك الحظر", "إدارة", "صلاحية حظر الأعضاء"),
        ("طرد عضو", "إدارة", "صلاحية حظر الأعضاء مع قرار منفصل"),
        ("كتم عضو بمدة", "إدارة", "صلاحية تقييد الأعضاء ومدة"),
        ("رفع الكتم", "إدارة", "صلاحية تقييد الأعضاء"),
        ("نظام إنذارات متدرج", "إدارة", "تخزين دائم وسياسة يحددها المشرفون"),
        ("سجل إجراءات المشرفين", "إدارة", "قاعدة بيانات وقناة سجل اختيارية"),
        ("بلاغ على رسالة", "إدارة", "قناة بلاغات وصلاحية نشر البوت"),
        ("استطلاع قرار المشرفين", "إدارة", "موافقة المشرفين قبل الإجراء الحساس"),
        ("تثبيت وإلغاء تثبيت", "إدارة", "صلاحية تثبيت الرسائل"),
        ("تنظيف رسائل مؤقت", "إدارة", "صلاحية حذف الرسائل ومدة سياسة الحذف"),
        ("جدولة إعلان المجموعة", "إدارة", "مخزن مهام وخدمة تشغيل مستمرة"),
    ],
    "حماية القروبات": [
        ("كابتشا للأعضاء الجدد", "حماية", "رسائل خاصة أو أزرار وإمكانية تقييد العضو"),
        ("مهلة التحقق", "حماية", "صلاحية تقييد وحذف أعضاء غير متحققين"),
        ("قائمة سماح للأعضاء", "حماية", "قاعدة بيانات وإدارة مشرف"),
        ("قائمة حظر نصية", "حماية", "قواعد كلمات يحددها المشرف"),
        ("قفل الروابط", "حماية", "صلاحية حذف الرسائل"),
        ("قفل دعوات القروبات", "حماية", "صلاحية حذف الرسائل"),
        ("قفل الوسائط", "حماية", "صلاحية حذف الرسائل"),
        ("قفل التحويلات", "حماية", "صلاحية حذف الرسائل"),
        ("قفل الرسائل الصوتية", "حماية", "صلاحية حذف الرسائل"),
        ("قفل الملصقات", "حماية", "صلاحية حذف الرسائل"),
        ("تحديد معدل الرسائل", "حماية", "ذاكرة مؤقتة أو Redis عند التوسع"),
        ("كشف تكرار الرسالة", "حماية", "ذاكرة رسائل حديثة"),
        ("كشف تشابه السبام", "حماية", "عينات spam وham ونموذج تصنيف"),
        ("كلمات توقف مطابقة جزئية", "حماية", "قائمة كلمات ومطابقة مضبوطة"),
        ("فحص سمعة العضو", "حماية", "مزود سمعة خارجي اختياري مع موافقة"),
        ("تحليل الرسالة بالذكاء الاصطناعي", "حماية", "مزود LLM مضبوط وحدود تكلفة"),
        ("فحص الصور الحساسة", "حماية", "نموذج رؤية وموافقة صريحة على تحليل الصور"),
        ("مراقبة الحسابات الآلية", "حماية", "إشارات سلوكية دون جمع بيانات زائدة"),
        ("وضع تجريبي بلا حذف", "حماية", "قاعدة بيانات لسجل النتائج فقط"),
        ("تعلّم من تصحيح المشرف", "حماية", "تسجيل عينات مصححة وسياسة احتفاظ"),
    ],
    "ألعاب القروبات": [
        ("مسابقة معلومات عامة", "لعبة", "قاعدة أسئلة أو مولد أسئلة مضبوط"),
        ("مسابقة سرعة الإجابة", "لعبة", "حالة جلسة مؤقتة ومنع الإجابات المكررة"),
        ("صح أو خطأ", "لعبة", "قاعدة أسئلة ونظام نقاط"),
        ("خمن الكلمة", "لعبة", "قاموس كلمات وإخفاء الإجابة"),
        ("خمن الشخصية", "لعبة", "محتوى أسئلة مرخص أو يكتبه المشرف"),
        ("ترتيب اللاعبين", "لعبة", "تخزين نقاط لكل مجموعة"),
        ("إنجازات اللعب", "لعبة", "سجل تقدم دائم"),
        ("مهمة يومية", "لعبة", "جدولة يومية ومنع التكرار"),
        ("تحدي أسبوعي", "لعبة", "نافذة زمنية وترتيب أسبوعي"),
        ("نظام فرق", "لعبة", "إدارة فرق وحالة مباراة"),
        ("مباراة إقصائية", "لعبة", "جلسة مباريات وتأكيد المشاركين"),
        ("لعبة أربع بصف", "لعبة", "حالة لوحة وتحقق من النقلات"),
        ("لعبة إكس أو", "لعبة", "حالة لوحة وتحقق من النقلات"),
        ("لعبة حجر ورق مقص", "لعبة", "جلسة قصيرة واختيار عشوائي آمن"),
        ("لعبة تخمين الرقم", "لعبة", "مولد عشوائي ونطاق يحدده المشرف"),
        ("نظام نقاط غير مالي", "لعبة", "قاعدة بيانات؛ لا تحويل مالي أو مقامرة"),
        ("متجر جوائز افتراضي", "لعبة", "جوائز داخلية يحددها الصانع دون قيمة نقدية"),
        ("أحداث عشوائية آمنة", "لعبة", "مولد عشوائي وسجل قابل للتدقيق"),
        ("كابتشا قبل المكافأة", "لعبة", "تحقق لمنع الحسابات الآلية"),
        ("مولد أسئلة بالذكاء الاصطناعي", "لعبة", "مزود LLM وفلتر إجابات ومراجعة مشرف"),
    ],
}

FEATURES: list[CommunityFeature] = []
_counter = 1
for category, rows in _RAW.items():
    for title, kind, requirement in rows:
        FEATURES.append(CommunityFeature(f"{_counter:03d}", title, category, kind, requirement))
        _counter += 1
FEATURE_BY_KEY = {item.key: item for item in FEATURES}
FEATURES_BY_CATEGORY = {category: [x for x in FEATURES if x.category == category] for category in _RAW}


def _categories_markup() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(category, callback_data=f"community:cat:{i}")] for i, category in enumerate(_RAW)]
    return InlineKeyboardMarkup(rows)


def _category_markup(category: str) -> InlineKeyboardMarkup:
    items = FEATURES_BY_CATEGORY[category]
    rows = [[InlineKeyboardButton(f"{x.key} — {x.title}", callback_data=f"community:item:{x.key}")] for x in items]
    rows.append([InlineKeyboardButton("التصنيفات", callback_data="community:home")])
    return InlineKeyboardMarkup(rows)


def _feature_text(item: CommunityFeature) -> str:
    return (f"الميزة {item.key}: {item.title}\n"
            f"التصنيف: {item.category}\n"
            f"النوع: {item.kind}\n"
            f"المتطلبات: {item.requirement}\n"
            f"الحالة: {item.status}\n\n"
            "هذه بطاقة متطلبات. لن ينفذ عز إجراءً إداريًا أو اتصالًا خارجيًا قبل التحقق من الصلاحيات والموافقة.")


async def community_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"ميزات الإدارة والحماية والألعاب: {len(FEATURES)} ميزة", reply_markup=_categories_markup())


async def community_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    if query.data == "community:home":
        await query.edit_message_text(f"ميزات الإدارة والحماية والألعاب: {len(FEATURES)} ميزة", reply_markup=_categories_markup())
        return
    if len(parts) == 3 and parts[1] == "cat":
        categories = list(_RAW)
        try:
            category = categories[int(parts[2])]
        except (ValueError, IndexError):
            await query.edit_message_text("التصنيف غير موجود.")
            return
        await query.edit_message_text(category, reply_markup=_category_markup(category))
        return
    if len(parts) == 3 and parts[1] == "item":
        item = FEATURE_BY_KEY.get(parts[2])
        if not item:
            await query.edit_message_text("الميزة غير موجودة.")
            return
        await query.edit_message_text(_feature_text(item), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="community:home")]]))


def register_community_handlers(application) -> None:
    application.add_handler(CommandHandler("community", community_command))
    application.add_handler(CallbackQueryHandler(community_callback, pattern=r"^community:"))
