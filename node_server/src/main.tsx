import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, Bot, Boxes, CheckCircle2, ChevronLeft, CloudCog, LayoutDashboard, Search, ShieldCheck, Sparkles, Terminal, Zap } from 'lucide-react';
import './styles.css';

type Service = { key: string; name: string; category: string; auth: string; requirement: string; status: string };
type Health = { status: string; uptime?: number; aiProvider?: string; catalogCount?: number };
declare global { interface Window { Telegram?: { WebApp: { ready: () => void; expand: () => void; sendData: (data: string) => void; initData?: string; initDataUnsafe?: { user?: { id: number; first_name?: string; username?: string } } } } } }
const telegramWebApp = () => window.Telegram?.WebApp;
const sendBotAction = (action: string, payload: Record<string, unknown> = {}) => telegramWebApp()?.sendData(JSON.stringify({ action, payload }));

const fallbackServices: Service[] = [
  ...['Rose Bot','MissRose','Combot','Group Help','Controller Bot','Shieldy','Skeddy Admin','Telegram Admin Bot','Group Butler','ChatKeeper'].map((name, i) => ({ key: `151${i}`, name, category: 'إدارة القروبات', auth: 'صلاحية مشرف Telegram', requirement: 'إضافة عز مشرفًا ومنحه الصلاحيات المطلوبة', status: 'بطاقة متطلبات' })),
  ...['CAS Anti-Spam','TG-Spam','Samurai Anti-Spam','eGenix Antispam','SpamWatch','Combot Anti-Spam','Shieldy CAPTCHA','LinkGuard','MediaLock','ModGuard'].map((name, i) => ({ key: `161${i}`, name, category: 'حماية القروبات', auth: 'API اختياري', requirement: 'قاعدة سياسات وموافقة الصانع قبل الحذف أو الحظر', status: 'بطاقة متطلبات' })),
  ...['Quiz Bot','Trivia Bot','Gamee','Quizarium','Werewolf Bot','Chess Bot','Connect Four Bot','Economy Bot','Word Game Bot','Team Battle Bot'].map((name, i) => ({ key: `171${i}`, name, category: 'ألعاب القروبات', auth: 'لا يحتاج اتصالًا خارجيًا', requirement: 'جلسة لعب وتخزين نقاط افتراضية فقط', status: 'بطاقة متطلبات' })),
];

function App() {
  const [services, setServices] = useState<Service[]>(fallbackServices);
  const [health, setHealth] = useState<Health>({ status: 'جاري الفحص', aiProvider: 'غير معروف' });
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('الكل');
  const [active, setActive] = useState('الرئيسية');

  useEffect(() => {
    telegramWebApp()?.ready();
    telegramWebApp()?.expand();
    Promise.all([
      fetch('/api/health').then(r => r.json()).catch(() => ({ status: 'غير متصل' })),
      fetch('/api/catalog').then(r => r.json()).catch(() => ({ services: fallbackServices })),
    ]).then(([h, c]) => {
      setHealth(h);
      if (Array.isArray(c.services) && c.services.length) setServices(c.services);
    });
  }, []);

  const categories = useMemo(() => ['الكل', ...Array.from(new Set(services.map(s => s.category)))], [services]);
  const filtered = useMemo(() => services.filter(s => (category === 'الكل' || s.category === category) && `${s.name} ${s.category}`.toLowerCase().includes(query.toLowerCase())), [services, category, query]);

  return <div className="shell">
    <aside className="sidebar glass">
      <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><strong>عز</strong><span>لوحة التشغيل</span></div></div>
      <nav>{[['الرئيسية', LayoutDashboard], ['كتالوج الخدمات', Boxes], ['الحماية', ShieldCheck], ['التشغيل 505F', Terminal], ['الإعدادات', CloudCog]].map(([label, Icon]) => <button className={active === label ? 'nav-item active' : 'nav-item'} onClick={() => setActive(label as string)} key={label as string}><Icon size={18} /><span>{label as string}</span></button>)}</nav>
      <div className="sidebar-foot"><span className="status-dot" /> عز متصل بالخادم</div>
    </aside>
    <main className="content">
      <header className="topbar"><div><p className="eyebrow">عز — فيصل العراقي</p><h1>{active}</h1><p className="muted">تحكم واضح وسريع بدون ازدحام.</p></div><div className="top-actions"><button className="icon-button" title="حالة النظام"><Activity size={18} /></button><div className="avatar">عز</div></div></header>
      {active === 'الرئيسية' && <><section className="hero glass"><div><span className="pill"><Zap size={14} /> وضع التشغيل السريع</span><h2>كل أدوات عز في مكان واحد.</h2><p>تابع الذكاء الاصطناعي، الخدمات، الحماية وتشغيل السكربتات من واجهة واحدة.</p><button className="primary" onClick={() => setActive('كتالوج الخدمات')}>فتح الكتالوج <ChevronLeft size={17} /></button></div><div className="hero-orb"><Bot size={74} strokeWidth={1.2} /></div></section><section className="stats-grid"><Stat icon={<Activity />} label="حالة البوت" value={health.status === 'ok' ? 'يعمل' : health.status} tone="green" /><Stat icon={<Boxes />} label="الخدمات" value={String(health.catalogCount || services.length)} tone="blue" /><Stat icon={<ShieldCheck />} label="الحماية" value="جاهزة للإعداد" tone="purple" /><Stat icon={<Zap />} label="المزود" value={health.aiProvider || 'متعدد'} tone="orange" /></section><section className="two-col"><div className="glass panel"><div className="panel-head"><h3>الوصول السريع</h3><span>اليوم</span></div><div className="quick-grid"><Quick icon={<ShieldCheck />} title="حماية القروب" text="السياسات والكابتشا" onClick={() => setActive('الحماية')} /><Quick icon={<Terminal />} title="تشغيل 505F" text="بيئة السكربتات" onClick={() => setActive('التشغيل 505F')} /><Quick icon={<Boxes />} title="كتالوج الخدمات" text={`${services.length} خدمة`} onClick={() => setActive('كتالوج الخدمات')} /></div></div><div className="glass panel activity-panel"><div className="panel-head"><h3>الحالة الآن</h3><span className="live"><i /> مباشر</span></div><p className="activity-line"><CheckCircle2 size={17} /> قناة Telegram جاهزة</p><p className="activity-line"><CheckCircle2 size={17} /> الذاكرة المستمرة مفعلة</p><p className="activity-line"><CheckCircle2 size={17} /> الصلاحيات الحساسة تتطلب تأكيدًا</p></div></section></>}
      {active === 'كتالوج الخدمات' && <section className="glass catalog-panel"><div className="panel-head"><div><h3>كتالوج الخدمات</h3><p className="muted">بطاقات متطلبات آمنة قبل أي ربط خارجي.</p></div><span className="count-badge">{filtered.length} نتيجة</span></div><div className="filters"><label className="search"><Search size={17} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="ابحث عن خدمة..." /></label><div className="chips">{categories.slice(-8).map(c => <button className={category === c ? 'chip selected' : 'chip'} onClick={() => setCategory(c)} key={c}>{c}</button>)}</div></div><div className="service-list">{filtered.map(s => <article className="service-card" key={s.key}><div className="service-icon"><Boxes size={18} /></div><div className="service-main"><h4>{s.name}</h4><span>{s.category}</span></div><div className="service-meta"><small>{s.auth}</small><p>{s.requirement}</p></div><span className="ready">{s.status}</span><button className="service-open" onClick={() => sendBotAction('open_service', { key: s.key })}>فتح</button></article>)}</div></section>}
      {active !== 'الرئيسية' && active !== 'كتالوج الخدمات' && <section className="glass empty-state"><div className="empty-icon"><Sparkles /></div><h2>{active}</h2><p>هذه المساحة جاهزة لربط المنفذ الفعلي مع واجهة عز الحديثة.</p><button className="primary" onClick={() => setActive('كتالوج الخدمات')}>استعراض الخدمات</button></section>}
    </main>
  </div>;
}
function Stat({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: string }) { return <div className={`glass stat ${tone}`}><div className="stat-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div>; }
function Quick({ icon, title, text, onClick }: { icon: React.ReactNode; title: string; text: string; onClick: () => void }) { return <button className="quick" onClick={onClick}><div className="quick-icon">{icon}</div><div><strong>{title}</strong><span>{text}</span></div><ChevronLeft size={16} /></button>; }

createRoot(document.getElementById('root')!).render(<App />);
