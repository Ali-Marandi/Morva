import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, History, RefreshCw, ShieldCheck } from 'lucide-react';
import { paymentExceptionService, PaymentException, PaymentExceptionEvent } from '../services/payment-exceptions';

const typeLabels: Record<string, string> = {
  return: 'برگشت', reject: 'رد', partial_settlement: 'تسویه ناقص', reversal: 'ابطال', unresolved_mismatch: 'مغایرت حل‌نشده',
};
const statusLabels: Record<string, string> = { open: 'باز', resolved: 'حل‌شده', blocked: 'مسدود' };

function PaymentExceptions() {
  const [records, setRecords] = useState<PaymentException[]>([]);
  const [selected, setSelected] = useState<PaymentException | null>(null);
  const [events, setEvents] = useState<PaymentExceptionEvent[]>([]);
  const [showResolved, setShowResolved] = useState(false);
  const [reason, setReason] = useState('');
  const [evidenceRef, setEvidenceRef] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try { setRecords(await paymentExceptionService.list(undefined, showResolved)); }
    catch (e) { setError(e instanceof Error ? e.message : 'خطا در دریافت استثناهای پرداخت.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [showResolved]);

  const openHistory = async (record: PaymentException) => {
    setSelected(record); setEvents([]); setError('');
    try { setEvents(await paymentExceptionService.events(record.exception_id)); }
    catch (e) { setError(e instanceof Error ? e.message : 'خطا در دریافت تاریخچه.'); }
  };

  const resolve = async () => {
    if (!selected || selected.status !== 'open' || reason.trim().length < 3 || !evidenceRef.trim()) return;
    setBusy(true); setError('');
    try {
      await paymentExceptionService.resolve(selected.exception_id, reason.trim(), evidenceRef.trim());
      setReason(''); setEvidenceRef(''); setSelected(null); setEvents([]); await load();
    } catch (e) { setError(e instanceof Error ? e.message : 'حل استثنای پرداخت انجام نشد.'); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-full bg-slate-100 p-5 md:p-7" dir="rtl">
      <div className="mx-auto max-w-7xl">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div><div className="flex items-center gap-2"><ShieldCheck size={21} className="text-blue-600" /><h1 className="text-2xl font-bold text-slate-900">استثناهای پرداخت</h1></div><p className="mt-1 text-sm text-slate-500">مدیریت provider-neutral مغایرت‌ها با ثبت دلیل و مستندات حل.</p></div>
            <div className="flex items-center gap-2">
              <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-700"><input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} /> نمایش حل‌شده‌ها</label>
              <button type="button" onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-medium hover:bg-slate-50"><RefreshCw size={17} /> به‌روزرسانی</button>
            </div>
          </div>
        </div>

        {error && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</div>}
        <div className="mt-5 grid gap-5 lg:grid-cols-[1.5fr_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-4"><div className="flex items-center gap-2 font-bold text-slate-800"><AlertTriangle size={19} className="text-amber-600" /> فهرست استثناها</div></div>
            {loading ? <div className="p-10 text-center text-sm text-slate-500">در حال دریافت اطلاعات…</div> : records.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">موردی برای نمایش وجود ندارد.</div> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead className="bg-slate-50 text-slate-600"><tr className="border-b border-slate-200 text-right"><th className="px-4 py-3">شناسه</th><th className="px-4 py-3">قلم پرداخت</th><th className="px-4 py-3">نوع</th><th className="px-4 py-3">وضعیت</th><th className="px-4 py-3">عملیات</th></tr></thead><tbody className="divide-y divide-slate-100">{records.map((record) => <tr key={record.exception_id} className="hover:bg-slate-50"><td className="px-4 py-3 font-mono text-xs">{record.exception_id}</td><td className="px-4 py-3 font-mono text-xs">{record.payment_item_id}</td><td className="px-4 py-3">{typeLabels[record.exception_type] || record.exception_type}</td><td className="px-4 py-3"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold">{statusLabels[record.status] || record.status}</span></td><td className="px-4 py-3"><button type="button" onClick={() => void openHistory(record)} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50"><History size={15} /> تاریخچه</button></td></tr>)}</tbody></table></div>}
          </section>

          <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {!selected ? <div className="py-10 text-center text-sm text-slate-500">برای مشاهده تاریخچه و عملیات، یک استثنا را انتخاب کنید.</div> : <>
              <h2 className="font-bold text-slate-900">جزئیات استثنا</h2>
              <div className="mt-4 space-y-2 text-sm"><div><span className="text-slate-500">شناسه:</span> <span className="font-mono">{selected.exception_id}</span></div><div><span className="text-slate-500">دلیل اولیه:</span> {selected.reason}</div></div>
              <div className="mt-5 border-t border-slate-200 pt-4"><h3 className="font-semibold text-slate-800">تاریخچه رویدادها</h3>{events.length === 0 ? <p className="mt-3 text-sm text-slate-500">رویداد ثبت‌شده‌ای نیست.</p> : <div className="mt-3 space-y-3">{events.map((event) => <div key={event.fingerprint} className="rounded-xl bg-slate-50 p-3 text-xs"><div className="flex items-center justify-between gap-3"><span className="font-semibold">{statusLabels[event.status] || event.status}</span><span className="font-mono text-slate-500">{event.actor}</span></div><p className="mt-1 text-slate-600">{event.reason}</p><p className="mt-1 font-mono text-[10px] text-slate-400">{event.fingerprint}</p></div>)}</div>}
              </div>
              {selected.status === 'open' && <div className="mt-5 border-t border-slate-200 pt-4"><h3 className="font-semibold text-slate-800">حل استثنا</h3><label className="mt-3 block text-xs font-semibold text-slate-600">دلیل حل<input value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label><label className="mt-3 block text-xs font-semibold text-slate-600">مرجع مستند<input value={evidenceRef} onChange={(e) => setEvidenceRef(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" placeholder="recon://case/..." /></label><button type="button" disabled={busy || reason.trim().length < 3 || !evidenceRef.trim()} onClick={() => void resolve()} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#2855b5] px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"><CheckCircle2 size={17} /> {busy ? 'در حال ثبت…' : 'ثبت حل استثنا'}</button></div>}
            </>}
          </aside>
        </div>
      </div>
    </div>
  );
}
export default PaymentExceptions;
