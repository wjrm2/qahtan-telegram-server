# مصادر بحث ميزات إدارة القروبات والحماية والألعاب

## الهدف
استخلاص أفكار وظائف من مشاريع عامة وإعادة تنفيذها داخل عز بصورة أصلية، مع عدم نسخ الكود أو الأسرار أو الاعتماديات غير الضرورية.

## مشاريع GitHub

| المشروع | المجال | الترخيص الظاهر | وظائف مفيدة مستخلصة |
|---|---|---|---|
| [WilliamButcherBot](https://github.com/thehamkercat/williambutcherbot) | إدارة قروبات | MIT | بنية وحدات قابلة للإضافة، أوامر إدارة، واجهة مساعدة، فصل bot/userbot، تشغيل Docker |
| [OdinRobot](https://github.com/OdinRobot/OdinRobot) | إدارة قروبات | GPL-3.0 | إدارة معيارية، تخزين SQLAlchemy، نظام إعدادات، فصل وظائف المشرف والمالك |
| [Samurai](https://github.com/Priler/samurai) | حماية وإشراف آلي | غير ظاهر في صفحة الاستخراج | مكافحة الشتائم، كشف السبام، كشف NSFW، نظام بلاغات، سمعة، إعلانات مجدولة، سجل ومراقبة، تعدد اللغات |
| [TG-Spam](https://github.com/umputun/tg-spam) | مكافحة السبام | MIT | تحليل احتمالي، تشابه الرسائل، كلمات حظر، فحص CAS اختياري، فحص LLM اختياري، قواعد الروابط والصور والتحويل، تعلم من عينات spam/ham، dry-run، API وواجهة إدارة، SQLite/PostgreSQL، إضافات Lua |
| [eGenix Telegram Antispam](https://github.com/eGenix/egenix-telegram-antispam-bot) | مكافحة تسجيلات السبام | يحتاج مراجعة LICENSE قبل أي اعتماد | التحقق من الأعضاء الجدد ومقاومة التسجيلات الآلية |
| [telegram-quizquickanswer](https://github.com/ptkdev/quizquickanswer-telegram-game-bot) | ألعاب | يحتاج مراجعة LICENSE قبل أي اعتماد | مسابقة جماعية وإجابات سريعة |
| [advanced-telegram-economy](https://github.com/halitsever/advanced-telegram-economy) | اقتصاد وألعاب | يحتاج مراجعة LICENSE قبل أي اعتماد | راتب تلقائي، كابتشا، أحداث عشوائية، ترتيب، ألعاب حظ؛ ستنفذ عز ألعابًا غير مالية ولا مقامرة |
| [telegram-economy-engine](https://github.com/cordova7/telegram-economy-engine) | اقتصاد ألعاب | يحتاج مراجعة LICENSE قبل أي اعتماد | اقتصاد منفصل لكل مجموعة، ألعاب نرد، قابلية تبديل backend؛ سيعاد تصميمه بنقاط افتراضية غير قابلة للسحب |

## مصادر YouTube والمصادر العامة

| المصدر | الوظيفة المستخلصة |
|---|---|
| [How to manage Telegram group by Telegram bot](https://www.youtube.com/watch?v=IkfPZJUKcew) | إعداد البوت كمشرف، إدارة الأعضاء والأوامر الأساسية |
| [How to stop spam in Telegram group](https://www.youtube.com/watch?v=cKTIEmGmFaQ) | كابتشا للأعضاء الجدد، حذف السبام، الحظر التلقائي |
| [MissRose anti-spam documentation](https://missrose.org/docs/anti-spam/) | Locks لأنواع الرسائل، قوائم حظر، مطابقة نصية، قواعد مخصصة |
| [AI-powered Telegram trivia workflow](https://n8n.io/workflows/5459-ai-powered-telegram-trivia-bot-with-auto-question-generation-and-user-management/) | توليد أسئلة، تتبع التقدم، إدارة المستخدمين، مسابقات دورية |

## قيود التنفيذ

لن يتم نسخ الشيفرة من أي مشروع. ستُعاد صياغة الوظائف داخل بنية عز الحالية، وستظهر الوظائف التي تحتاج صلاحيات Telegram أو مفتاح خدمة أو نموذجًا محليًا كبطاقة متطلبات بدل الادعاء بأنها مفعلة. يجب مراجعة ترخيص كل مستودع قبل اقتباس أي جزء من الشيفرة، والالتزام بشروط GPL إن استُخدم كود مرخص بها؛ الافتراضي هو تنفيذ مستقل بلا نسخ.

## baseline الحالي

الجرد البنيوي الحالي لمستودع عز سجل 140 خدمة في الكتالوج، و87 تسجيلًا للأوامر/الأحداث، و140 دالة Python. الجرد يتعامل مع كتالوج الخدمات بتحليل AST حتى لا يحتاج إلى تثبيت مكتبة Telegram أثناء التدقيق.
