import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Download, FilePlus2, ListFilter, RefreshCw, Search, Trash2, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { findModuleItem } from '../config/moduleNavigation';

type DemoRow = { id: string; code: string; title: string; status: 'فعال' | 'در انتظار' | 'غیرفعال'; updatedAt: string };
const DEMO_ROWS: DemoRow[] = [
  { id: '1', code: 'M-001', title: 'رکورد نمونه اول', status: 'فعال', updatedAt: '۱۴۰۵/۰۶/۲۴' },
  { id: '2', code: 'M-002', title: 'رکورد نمونه دوم', status: 'در انتظار', updatedAt: '۱۴۰۵/۰۶/۲۳' },
  { id: '3', code: 'M-003', title: 'رکورد نمونه سوم', status: 'فعال', updatedAt: '۱۴۰۵/۰۶/۲۲' },
];
const storageKey = (id: string) => `morva_demo_workspace_${id}`;

function ModuleWorkspace() {
  const location = useLocation();
  const navigate = useNavigate();
  const parts = location.pathname.split('/').filter(Boolean);
  const id = parts.length ? parts[parts.length - 1] : '';
  const item = findModuleItem(id);
  const title = item?.label || 'بخش سامانه';
  const [rows, setRows] = useState<DemoRow[]>([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<'همه' | DemoRow['status']>('همه');
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCode, setNewCode] = useState('');

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(storageKey(id));
      setRows(stored ? JSON.parse(stored) : DEMO_ROWS);
    } catch { setRows(DEMO_ROWS); }
    setSearch('');
    setStatus('همه');
  }, [id]);

  useEffect(() => {
    if (id) window.localStorage.setItem(storageKey(id), JSON.stringify(rows));
  }, [id, rows]);

  const filteredRows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesSearch = !needle || [row.code, row.title, row.status].some((value) => value.toLowerCase().includes(needle));
      const matchesStatus = status === 'همه' || row.status === status;
      return matchesSearch && matchesStatus;
    });
  }, [rows, search, status]);

  const createRow = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const titleValue = newTitle.trim();
    const codeValue = newCode.trim();
    if (!titleValue || !codeValue) return;
    setRows((current) => [{ id: String(Date.now()), code: codeValue, title: titleValue, status: 'فعال', updatedAt: new Intl.DateTimeFormat('fa-IR').format(new Date()) }, ...current]);
    setNewTitle(''); setNewCode(''); setShowCreate(false);
  };

  const resetDemo = () => { setRows(DEMO_ROWS); setSearch(''); setStatus('همه'); };

  const exportCsv = () => {
    const header = ['کد', 'عنوان', 'وضعیت', 'آخرین به‌روزرسانی'];
    const lines = filteredRows.map((row) => [row.code, row.title, row.status, row.updatedAt]);
    const csv = [header, ...lines].map((line) => line.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = `morva-${id || 'workspace'}.csv`; link.click(); URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-full bg-slate-100 p-5 md:p-7" dir="rtl">
      <div className="mx-auto max-w-7xl">
        <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div><p className="text-xs font-medium text-slate-500">سیستم حقوق و دستمزد / مدیریت اطلاعات</p><h1 className="mt-1 text-2xl font-bold text-slate-800">{title}</h1><p className="mt-1 text-sm text-slate-500">محیط نمایشی قابل تعامل؛ تغییرات این بخش در مرورگر شما نگهداری می‌شود.</p></div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={exportCsv} disabled={!filteredRows.length} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"><Download size={17} /> خروجی CSV</button>
              <button type="button" onClick={resetDemo} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"><RefreshCw size={17} /> بازیابی نمونه</button>
              <button type="button" onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-lg bg-[#2855b5] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1f4599]"><FilePlus2 size={18} /> ایجاد مورد جدید</button>
            </div>
          </div>
        </div>
        <div className="mt-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center">
            <div className="flex items-center gap-2 text-slate-700 lg:min-w-48"><ListFilter size={19} className="text-[#2855b5]" /><span className="font-semibold">فهرست {title}</span><span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">{filteredRows.length} مورد</span></div>
            <div className="flex flex-1 flex-col gap-2 sm:flex-row">
              <div className="relative flex-1"><Search size={18} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="جست‌وجو در کد، عنوان یا وضعیت" className="w-full rounded-lg border border-slate-300 py-2.5 pr-10 pl-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" /></div>
              <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"><option value="همه">همه وضعیت‌ها</option><option value="فعال">فعال</option><option value="در انتظار">در انتظار</option><option value="غیرفعال">غیرفعال</option></select>
            </div>
          </div>
          {filteredRows.length === 0 ? <div className="p-12 text-center"><p className="font-semibold text-slate-700">موردی برای نمایش پیدا نشد.</p><p className="mt-2 text-sm text-slate-500">عبارت جست‌وجو یا فیلتر وضعیت را تغییر دهید، یا یک مورد جدید بسازید.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-sm"><thead className="bg-slate-50 text-slate-600"><tr className="border-b border-slate-200 text-right"><th className="px-5 py-3 font-semibold">کد</th><th className="px-5 py-3 font-semibold">عنوان</th><th className="px-5 py-3 font-semibold">وضعیت</th><th className="px-5 py-3 font-semibold">آخرین به‌روزرسانی</th><th className="px-5 py-3 text-left font-semibold">عملیات</th></tr></thead><tbody className="divide-y divide-slate-100">{filteredRows.map((row) => <tr key={row.id} className="hover:bg-slate-50/80"><td className="px-5 py-3 font-mono text-slate-700">{row.code}</td><td className="px-5 py-3 font-medium text-slate-900">{row.title}</td><td className="px-5 py-3"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${row.status === 'فعال' ? 'bg-emerald-50 text-emerald-700' : row.status === 'در انتظار' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>{row.status}</span></td><td className="px-5 py-3 text-slate-600">{row.updatedAt}</td><td className="px-5 py-3 text-left"><button type="button" onClick={() => setRows((current) => current.filter((item) => item.id !== row.id))} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50" aria-label={`حذف ${row.title}`}><Trash2 size={15} /> حذف</button></td></tr>)}</tbody></table></div>}
        </div>
        {item?.children && item.children.length > 0 && <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-bold text-slate-800">دسترسی‌های مرتبط</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{item.children.map((child) => <button key={child.id} type="button" onClick={() => navigate(`/modules/${child.id}`)} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right text-sm font-medium text-slate-700 hover:border-blue-200 hover:bg-blue-50 hover:text-[#244da8]"><span>{child.label}</span><ArrowLeft size={17} /></button>)}</div></div>}
      </div>
      {showCreate && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/40 p-4" role="dialog" aria-modal="true" aria-labelledby="create-workspace-item"><div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl"><div className="flex items-center justify-between gap-4"><div><h2 id="create-workspace-item" className="text-lg font-bold text-slate-900">ایجاد مورد جدید</h2><p className="mt-1 text-xs text-slate-500">این رکورد فقط در محیط نمایشی ذخیره می‌شود.</p></div><button type="button" onClick={() => setShowCreate(false)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="بستن"><X size={20} /></button></div><form onSubmit={createRow} className="mt-5 space-y-4"><div><label htmlFor="workspace-code" className="mb-1.5 block text-sm font-semibold text-slate-800">کد</label><input id="workspace-code" value={newCode} onChange={(event) => setNewCode(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" placeholder="مثلاً M-004" required /></div><div><label htmlFor="workspace-title" className="mb-1.5 block text-sm font-semibold text-slate-800">عنوان</label><input id="workspace-title" value={newTitle} onChange={(event) => setNewTitle(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" placeholder="عنوان مورد" required autoFocus /></div><div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">انصراف</button><button type="submit" className="rounded-lg bg-[#2855b5] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1f4599]">ثبت مورد</button></div></form></div></div>}
    </div>
  );
}
export default ModuleWorkspace;
