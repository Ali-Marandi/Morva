import React, { useState } from 'react';
import { ArrowLeft, Menu, ShieldCheck, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ModuleItem, moduleMenus } from '../../config/moduleNavigation';

function Topbar() {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const navigate = useNavigate();
  const current = moduleMenus.find((menu) => menu.id === activeMenu);
  const openPage = (item: ModuleItem) => { navigate(`/modules/${item.id}`); setActiveMenu(null); };

  return <header className="relative z-50 bg-[#244da8] text-white shadow-md" dir="rtl" onMouseLeave={() => setActiveMenu(null)}>
    <div className="flex min-h-14 items-center px-3 lg:px-5">
      <div className="ml-4 hidden items-center gap-2 whitespace-nowrap xl:flex"><div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/50"><ShieldCheck size={18} /></div><span className="text-sm font-bold">سیستم حقوق و دستمزد</span></div>
      <nav className="flex flex-1 items-center overflow-x-auto" aria-label="ماژول‌های سامانه">
        {moduleMenus.map((menu) => { const Icon = menu.icon; const isOpen = activeMenu === menu.id; return <button key={menu.id} type="button" onMouseEnter={() => setActiveMenu(menu.id)} onClick={() => setActiveMenu(isOpen ? null : menu.id)} className={`flex shrink-0 items-center gap-2 rounded-t-xl px-3 py-3.5 text-sm font-semibold transition-colors ${isOpen ? 'bg-white text-[#244da8]' : 'hover:bg-white/15'}`}><Icon size={17} />{menu.label}</button>; })}
      </nav>
      <button type="button" className="mr-2 rounded-lg p-2 hover:bg-white/15" onClick={() => setActiveMenu(activeMenu ? null : moduleMenus[0].id)} aria-label="باز کردن منو"><Menu size={21} /></button>
      <div className="mr-2 hidden items-center gap-2 border-r border-white/30 pr-3 sm:flex"><div className="text-left leading-tight"><p className="text-xs font-medium">مدیر سامانه</p><p className="text-[10px] text-white/70">حساب محلی</p></div><User size={20} /></div>
    </div>
    {current && <MegaMenu menu={current} onSelect={openPage} />}
  </header>;
}

function MegaMenu({ menu, onSelect }: { menu: ModuleItem; onSelect: (item: ModuleItem) => void }) {
  return <div className="absolute right-3 left-3 top-full rounded-b-2xl bg-white p-5 text-slate-800 shadow-2xl ring-1 ring-black/10 md:left-auto md:w-[min(920px,calc(100vw-24px))]">
    <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3"><div><p className="text-base font-bold text-slate-900">{menu.label}</p><p className="mt-0.5 text-xs text-slate-500">دسترسی سریع به بخش‌های مرتبط</p></div><button type="button" onClick={() => onSelect(menu)} className="inline-flex items-center gap-1 text-sm font-medium text-[#2855b5] hover:text-[#173979]">نمای کلی <ArrowLeft size={16} /></button></div>
    <div className="grid gap-x-6 gap-y-2 md:grid-cols-2 lg:grid-cols-3">
      {menu.children?.map((item) => <section key={item.id} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3 transition-colors hover:border-blue-100 hover:bg-blue-50/60">
        <button type="button" onClick={() => onSelect(item)} className="flex w-full items-center justify-between text-right text-sm font-bold text-slate-800"><span>{item.label}</span><ArrowLeft size={16} className="text-[#4d7ee8]" /></button>
        {item.children && <div className="mt-2 border-r border-blue-100 pr-3 space-y-1">{item.children.map((child) => <button key={child.id} type="button" onClick={() => onSelect(child)} className="block w-full rounded-md px-1 py-1.5 text-right text-xs text-slate-600 hover:bg-white hover:text-[#1d4ba9]">{child.label}</button>)}</div>}
      </section>)}
    </div>
  </div>;
}

export default Topbar;
