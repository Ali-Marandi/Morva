import React from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, Calculator, Users, FileText, AlertTriangle } from "lucide-react";
import "./styles.css";

const stats = [
  ["کارکنان", "103,482", Users],
  ["پرداخت این ماه", "آماده بررسی", Calculator],
  ["احکام منتظر کنترل", "37", FileText],
  ["هشدارهای مالی", "84", AlertTriangle],
];

function App() {
  return (
    <main className="shell">
      <header className="topbar"><div><strong>مروا</strong><span>Morva Payroll Platform</span></div><div className="badge"><ShieldCheck size={16}/> محیط کنترل مالی</div></header>
      <section className="hero"><div><p className="eyebrow">سامانه جامع حقوق و دستمزد</p><h1>هر حکم، یک قانون. هر ریال، قابل توضیح.</h1><p>مرکز کنترل کارگزینی، احکام، محاسبات حقوق، کسورات و حسابرسی.</p></div></section>
      <section className="grid">{stats.map(([label, value, Icon]) => <article className="card" key={label as string}><Icon size={21}/><span>{label}</span><strong>{value}</strong></article>)}</section>
      <section className="panel"><div className="panel-head"><h2>چرخه حقوق ماه جاری</h2><span>1405/06</span></div><div className="steps">{["دریافت اطلاعات", "محاسبه", "کنترل مغایرت", "تأیید", "پرداخت"].map((item, i) => <div className={i < 3 ? "step active" : "step"} key={item}><b>{i+1}</b>{item}</div>)}</div></section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
