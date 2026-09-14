import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, FilePlus2, ListFilter, Search } from 'lucide-react';
import { findModuleItem } from '../config/moduleNavigation';

function ModuleWorkspace() {
  const location = useLocation();
  const navigate = useNavigate();
  const id = location.pathname.split('/').filter(Boolean).at(-1) || '';
  const item = findModuleItem(id);
  const title = item?.label || 'بخش سامانه';

  return <div className="min-h-full bg-slate-100 p-5 md:p-7" dir="rtl">
    <div className="mx-auto max-w-6xl">
      <div className="rounded-xl bg-white px-5 py-4 shadow-sm border border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div><p className="text-sm text-slate-500">سیستم حقوق و دستمزد / مدیریت برنامه حقوقی</p><h1 className="mt-1 text-2xl font-bold text-slate-800">{title}</h1></div>
        <div className="flex gap-2"><button className="inline-flex items-center gap-2 rounded-lg bg-[#2855b5] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1f4599]"><FilePlus2 size={18} />ایجاد مورد جدید</button><button className="rounded-lg border border-slate-300 p-2.5 text-slate-600 hover:bg-slate-50"><Search size={19} /></button></div>
      </div>
      <div className="mt-5 rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4 flex items-center gap-2 text-slate-700"><ListFilter size={19} className="text-[#2855b5]" /><span className="font-semibold">فهرست {title}</span></div>
        <div className="p-10 text-center text-slate-500"><p className="font-medium">این بخش برای ثبت، جست‌وجو و مدیریت اطلاعات آماده است.</p><p className="mt-2 text-sm">داده‌های اکسل را می‌توانید از بخش «واردسازی اکسل» بارگذاری کنید.</p></div>
      </div>
      {item?.children && <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-bold text-slate-800">دسترسی‌های این بخش</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{item.children.map((child) => <button key={child.id} type="button" onClick={() => navigate(`/modules/${child.id}`)} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right text-sm font-medium text-slate-700 hover:border-blue-200 hover:bg-blue-50 hover:text-[#244da8]"><span>{child.label}</span><ArrowLeft size={17} /></button>)}</div></div>}
    </div>
  </div>;
}

export default ModuleWorkspace;
