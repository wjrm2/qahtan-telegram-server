"""Catalog of supported integrations and safe UI helpers.

The catalog is intentionally metadata-first: a button can always show the
requirements and current integration status without pretending that OAuth/API
credentials are configured. Actual providers are enabled one by one through
least-privilege adapters.
"""
from dataclasses import dataclass
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    category: str
    auth: str
    requirement: str
    status: str = "كتالوج؛ يحتاج إعدادًا"


_GROUPS = {
    "الهوية والحسابات": "Google,Microsoft,Apple,GitHub,GitLab,Bitbucket,LinkedIn,Auth0,Okta,Clerk",
    "التواصل": "Telegram,Discord,Slack,Microsoft Teams,WhatsApp Business,Twilio,Gmail,Outlook Mail,Yahoo Mail,Zoom",
    "التخزين والملفات": "Google Drive,OneDrive,Dropbox,Box,S3,Cloudflare R2,Backblaze B2,SharePoint,Egnyte,WeTransfer",
    "الإنتاجية": "Google Calendar,Outlook Calendar,Notion,Evernote,Todoist,Trello,Asana,Basecamp,Calendly,Miro",
    "المشاريع وCRM": "Jira,Linear,ClickUp,Monday.com,Airtable,Confluence,Salesforce,HubSpot,Pipedrive,Freshdesk",
    "النشر والبنية": "Vercel,Netlify,Cloudflare,Docker Hub,Kubernetes,DigitalOcean,AWS,Azure DevOps,Jenkins,Terraform Cloud",
    "البيانات وقواعد البيانات": "Google Sheets,BigQuery,Snowflake,PostgreSQL,MySQL,MongoDB,Redis,Supabase,Firebase,Elasticsearch",
    "التجارة والدفع": "Shopify,WooCommerce,Stripe,PayPal,Square,Amazon Seller,Mercado Pago,Magento,PrestaShop,BigCommerce",
    "المحتوى والإعلام": "YouTube,Vimeo,Twitch,TikTok for Developers,WordPress,Medium,RSS,Substack,Ghost,Webflow",
    "الذكاء الاصطناعي": "OpenAI,Anthropic,Gemini,Mistral,Cohere,Groq,Hugging Face,Replicate,Stability AI,ElevenLabs",
    "الشبكات الاجتماعية": "Facebook Pages,Instagram Graph,X/Twitter,Reddit,Pinterest,Snapchat,Threads,Mastodon,Bluesky,Buffer",
    "الخرائط والطقس": "Google Maps,Mapbox,HERE,OpenStreetMap,Foursquare,WeatherAPI,OpenWeather,AccuWeather,FlightAware,OpenSky",
    "الأمن والمراقبة": "1Password,Bitwarden,HashiCorp Vault,Cloudflare Zero Trust,Snyk,Dependabot,Sentry,Datadog,UptimeRobot,SonarQube",
    "الأتمتة والأجهزة": "Zapier,Make,n8n,GitHub Actions,Home Assistant,Philips Hue,HomeKit,SmartThings,IFTTT,MQTT",
}


def _make_services() -> List[Service]:
    services: List[Service] = []
    index = 1
    for category, names in _GROUPS.items():
        for name in names.split(","):
            key = f"{index:03d}"
            auth = "OAuth 2.0" if name not in {"S3", "Cloudflare R2", "Backblaze B2", "PostgreSQL", "MySQL", "MongoDB", "Redis", "MQTT", "RSS"} else "مفتاح API/اتصال خاص"
            requirement = "موافقة الصانع على الصلاحيات المطلوبة، وبيانات تطبيق OAuth أو مفتاح API محفوظ في الخزنة"
            services.append(Service(key, name, category, auth, requirement))
            index += 1
    return services


SERVICES = _make_services()
SERVICE_BY_KEY = {service.key: service for service in SERVICES}
PAGE_SIZE = 10


def catalog_categories() -> InlineKeyboardMarkup:
    rows = []
    for category in _GROUPS:
        rows.append([InlineKeyboardButton(f"🔗 {category}", callback_data=f"svc_cat:{category}")])
    rows.append([InlineKeyboardButton("🧪 فحص الكتالوج", callback_data="svc_check")])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="cb_back")])
    return InlineKeyboardMarkup(rows)


def catalog_page(page: int = 0, category: str | None = None) -> InlineKeyboardMarkup:
    items = [s for s in SERVICES if category is None or s.category == category]
    start = max(0, page) * PAGE_SIZE
    rows = []
    for service in items[start:start + PAGE_SIZE]:
        rows.append([InlineKeyboardButton(f"🔗 {service.name}", callback_data=f"svc:{service.key}")])
    nav = []
    if start > 0:
        suffix = f":{category}" if category else ""
        nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"svc_page:{page-1}{suffix}"))
    if start + PAGE_SIZE < len(items):
        suffix = f":{category}" if category else ""
        nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"svc_page:{page+1}{suffix}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("📚 التصنيفات", callback_data="svc_catalog")])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="cb_back")])
    return InlineKeyboardMarkup(rows)


def service_text(service: Service) -> str:
    return (
        f"🔗 <b>{service.name}</b>\n"
        f"التصنيف: {service.category}\n"
        f"المصادقة: {service.auth}\n"
        f"المتطلبات: {service.requirement}\n"
        f"الحالة: {service.status}\n\n"
        "لن يتم حفظ كلمة المرور. الربط الفعلي يحتاج موافقة صريحة وصلاحيات محددة، "
        "وستظهر العمليات الحساسة كتأكيد مستقل قبل التنفيذ."
    )


def catalog_check_text() -> str:
    categories = len(_GROUPS)
    return (
        f"🧪 فحص الكتالوج مكتمل\n"
        f"الخدمات المفهرسة: {len(SERVICES)}\n"
        f"التصنيفات: {categories}\n"
        "الأزرار تعرض بطاقة المتطلبات حتى قبل إعداد credentials.\n"
        "الحالة الحالية: كتالوج آمن؛ لا توجد صلاحيات خارجية مفعّلة تلقائيًا."
    )
