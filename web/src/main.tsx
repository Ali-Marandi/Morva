import React from "react";
import { createRoot } from "react-dom/client";
import { Database, FileSearch, LockKeyhole, Scale, ShieldCheck, UserRound } from "lucide-react";
import "./styles.css";

const lifecycle = ["پیش‌نویس", "دریافت داده", "محاسبه", "اعتبارسنجی", "بررسی", "تأیید", "قفل", "خروجی", "ارسال", "تأیید پرداخت", "مغایرت‌گیری"];

const roles = [
  { title: "کارشناس مالی منطقه", icon: Database, items: ["صف ورود داده", "مغایرت‌ها", "کنترل محاسبه", "خروجی‌های تأییدشده"] },
  { title: "کارگزینی", icon: UserRound, items: ["احکام مؤثر", "تغییرات پرسنلی", "رتبه‌بندی", "گردش تأیید"] },
  { title: "مدیر / تأییدکننده", icon: ShieldCheck, items: ["ریسک و استثنا", "مقایسه دوره‌ای", "تأیید مرحله‌ای", "تفکیک وظایف"] },
  { title: "حسابرس", icon: FileSearch, items: ["زنجیره حسابرسی", "بازسازی فیش", "ردیابی Rule Pack", "مغایرت پرداخت"] },
  { title: "کارمند", icon: Scale, items: ["فیش حقوقی", "تاریخچه", "توضیح هر قلم", "اعتراض و پیگیری"] },
];

function App() {
  return (
    <main className="shell" dir="rtl">
      <header className="topbar">
        <div><strong>مروا</strong><span>Morva Payroll Platform</span></div>
        <div className="badge"><ShieldCheck size={16}/> کنترل مالی</div>
      </header>

      <section className="hero">
        <p className="eyebrow">سامانه جامع حقوق و دستمزد</p>
        <h1>هر حکم، یک قانون. هر ریال، قابل توضیح.</h1>
        <p>گردش کنترل‌شده حقوق، احکام، مغایرت‌گیری و حسابرسی با اصل «داده واقعی یا وضعیت نامشخص».</p>
      </section>

      <section className="grid">
        <article className="card">
          <Database size={21}/>
          <span>وضعیت منبع داده</span>
          <strong>داده عملیاتی متصل نیست</strong>
          <small>هیچ عدد یا تعداد ساختگی نمایش داده نمی‌شود.</small>
        </article>
        <article className="card">
          <LockKeyhole size={21}/>
          <span>محیط پرداخت</span>
          <strong>قفل ایمنی</strong>
          <small>بدون Rule Pack و اتصال رسمی، ارسال پرداخت مجاز نیست.</small>
        </article>
        <article className="card">
          <ShieldCheck size={21}/>
          <span>هویت و مجوز</span>
          <strong>نیازمند احراز سازمانی</strong>
          <small>عملیات حساس به هویت، حوزه سازمانی و MFA وابسته است.</small>
        </article>
        <article className="card">
          <Scale size={21}/>
          <span>قواعد حقوقی</span>
          <strong>Fail Closed</strong>
          <small>قاعده بدون سند اولیه و تأیید رسمی فعال نمی‌شود.</small>
        </article>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>صفحات عملیاتی نقش‌ها</h2>
          <span>رابط آماده است؛ داده عملیاتی فقط از API احراز‌شده می‌آید.</span>
        </div>
        <div className="role-grid">
          {roles.map(({ title, icon: Icon, items }) => (
            <article className="role-card" key={title}>
              <div className="role-title"><Icon size={20}/><strong>{title}</strong></div>
              <ul>
                {items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>چرخه حقوق</h2>
          <span>فقط پس از اتصال امن و تأیید Rule Pack</span>
        </div>
        <div className="steps">
          {lifecycle.map((item, i) => (
            <div className="step" key={item}>
              <b>{i + 1}</b>{item}
            </div>
          ))}
        </div>
        <p className="notice">وضعیت فعلی این رابط نمایشی است؛ تا زمان اتصال سرویس احراز‌شده هیچ وضعیت تجاری یا مبلغ واقعی ادعا نمی‌شود.</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
