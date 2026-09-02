import React from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, Database, LockKeyhole } from "lucide-react";
import "./styles.css";

function App() {
  return (
    <main className="shell" dir="rtl">
      <header className="topbar">
        <div><strong>مروا</strong><span>Morva Payroll Platform</span></div>
        <div className="badge"><ShieldCheck size={16}/> کنترل مالی</div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">سامانه جامع حقوق و دستمزد</p>
          <h1>هر حکم، یک قانون. هر ریال، قابل توضیح.</h1>
          <p>کارگزینی، احکام، محاسبات حقوق، مغایرت‌گیری و حسابرسی در یک چرخهٔ کنترل‌شده.</p>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <Database size={21}/>
          <span>وضعیت داده عملیاتی</span>
          <strong>متصل نیست</strong>
        </article>
        <article className="card">
          <LockKeyhole size={21}/>
          <span>محیط پرداخت</span>
          <strong>قفل ایمنی</strong>
        </article>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>چرخه حقوق</h2>
          <span>فقط پس از اتصال امن و تأیید Rule Pack</span>
        </div>
        <div className="steps">
          {["پیش‌نویس", "دریافت داده", "محاسبه", "اعتبارسنجی", "بررسی", "تأیید", "قفل", "خروجی", "ارسال", "تأیید پرداخت", "مغایرت‌گیری"].map((item, i) => (
            <div className="step" key={item}>
              <b>{i + 1}</b>{item}
            </div>
          ))}
        </div>
        <p className="notice">هیچ شاخص، مبلغ یا وضعیت عملیاتی ساختگی در این رابط نمایش داده نمی‌شود.</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
