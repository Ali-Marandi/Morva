import React, { useState } from 'react';
import { BriefcaseBusiness, Download, FileText, UserRound, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { selfService } from '@/services/self-service';

const money = (value: string) => new Intl.NumberFormat('fa-IR').format(Number(value));
const date = (value: string) => new Intl.DateTimeFormat('fa-IR').format(new Date(value));

function SelfService() {
  const [period, setPeriod] = useState('');
  const [selectedPayslipId, setSelectedPayslipId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const profile = useQuery({ queryKey: ['self', 'profile'], queryFn: selfService.getProfile });
  const payslips = useQuery({
    queryKey: ['self', 'payslips', period],
    queryFn: () => selfService.getPayslips(period || undefined),
  });
  const orders = useQuery({ queryKey: ['self', 'orders'], queryFn: selfService.getOrders });
  const selectedPayslip = useQuery({
    queryKey: ['self', 'payslip', selectedPayslipId],
    queryFn: () => selfService.getPayslip(selectedPayslipId as string),
    enabled: Boolean(selectedPayslipId),
  });

  const downloadPdf = async (artifactId: string, payslipPeriod: string) => {
    setDownloadError(null);
    setDownloadingId(artifactId);
    try {
      const response = await selfService.getPayslipPdf(artifactId);
      const blob = response instanceof Blob
        ? response
        : new Blob([response as unknown as BlobPart], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `payslip-${payslipPeriod}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setDownloadError('دریافت فایل PDF ناموفق بود. وضعیت فیش را بررسی کرده و دوباره تلاش کنید.');
    } finally {
      setDownloadingId(null);
    }
  };

  const profileData = profile.data?.data;
  const payslipItems = payslips.data?.data ?? [];
  const orderItems = orders.data?.data ?? [];
  const detail = selectedPayslip.data?.data;

  return (
    <div className="space-y-6 p-6" dir="rtl">
      <header>
        <h1 className="text-3xl font-bold text-morva-900">خدمات کارکنان</h1>
        <p className="mt-2 text-morva-600">اطلاعات شخصی، فیش حقوقی و احکام فقط از مسیر احراز‌شده سامانه.</p>
      </header>

      {profile.isError && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">دریافت پروفایل ناموفق بود.</div>}
      {profile.isLoading && <div className="rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-600">در حال دریافت پروفایل…</div>}
      {profileData && (
        <section className="rounded-xl border border-morva-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3"><UserRound size={22} /><h2 className="text-lg font-bold">پروفایل پرسنلی</h2></div>
          <div className="grid gap-4 text-sm md:grid-cols-4">
            <div><span className="text-morva-500">نام</span><div className="mt-1 font-semibold">{profileData.first_name} {profileData.last_name}</div></div>
            <div><span className="text-morva-500">کد کارمند</span><div className="mt-1 font-semibold">{profileData.employee_no}</div></div>
            <div><span className="text-morva-500">نوع استخدام</span><div className="mt-1 font-semibold">{profileData.employment_type}</div></div>
            <div><span className="text-morva-500">وضعیت</span><div className="mt-1 font-semibold">{profileData.status}</div></div>
          </div>
        </section>
      )}

      <section className="rounded-xl border border-morva-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3"><FileText size={22} /><h2 className="text-lg font-bold">فیش‌های حقوقی</h2></div>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-morva-600">دوره</span>
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="۱۴۰۵-۰۶" inputMode="numeric" aria-label="دوره فیش حقوقی" className="w-32 rounded-lg border border-morva-300 px-3 py-2 text-right" />
            {period && <button type="button" onClick={() => setPeriod('')} className="text-sm font-semibold text-morva-700">حذف فیلتر</button>}
          </label>
        </div>

        {downloadError && <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{downloadError}</div>}
        {payslips.isLoading && <p className="text-sm text-morva-600">در حال دریافت فیش‌ها…</p>}
        {payslips.isError && <p role="alert" className="text-sm text-red-700">دریافت فیش‌ها ناموفق بود.</p>}
        {!payslips.isLoading && !payslips.isError && payslipItems.length === 0 && <p className="text-sm text-morva-600">فیش قابل نمایش وجود ندارد.</p>}
        {payslipItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-morva-200 text-right"><th className="px-3 py-3">دوره</th><th className="px-3 py-3">وضعیت</th><th className="px-3 py-3">ناخالص</th><th className="px-3 py-3">کسورات</th><th className="px-3 py-3">خالص</th><th className="px-3 py-3">عملیات</th></tr></thead>
              <tbody>
                {payslipItems.map((item) => (
                  <tr key={item.artifact_id} className="border-b border-morva-100">
                    <td className="px-3 py-3 font-medium">{item.period}</td>
                    <td className="px-3 py-3">{item.status}</td>
                    <td className="px-3 py-3">{money(item.gross)} {item.currency_code}</td>
                    <td className="px-3 py-3">{money(item.deductions)} {item.currency_code}</td>
                    <td className="px-3 py-3 font-semibold">{money(item.net)} {item.currency_code}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => setSelectedPayslipId(item.artifact_id)} className="rounded-lg border border-morva-300 px-3 py-2 font-semibold text-morva-800 hover:bg-morva-50">جزئیات</button>
                        <button type="button" disabled={downloadingId === item.artifact_id} onClick={() => downloadPdf(item.artifact_id, item.period)} className="inline-flex items-center gap-2 rounded-lg bg-morva-600 px-3 py-2 text-white hover:bg-morva-700 disabled:cursor-not-allowed disabled:opacity-60">
                          <Download size={16} />{downloadingId === item.artifact_id ? 'در حال دریافت…' : 'PDF'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-morva-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-3"><BriefcaseBusiness size={22} /><h2 className="text-lg font-bold">احکام پرسنلی</h2></div>
        {orders.isLoading && <p className="text-sm text-morva-600">در حال دریافت احکام…</p>}
        {orders.isError && <p role="alert" className="text-sm text-red-700">دریافت احکام ناموفق بود.</p>}
        {!orders.isLoading && !orders.isError && orderItems.length === 0 && <p className="text-sm text-morva-600">حکم قابل نمایش وجود ندارد.</p>}
        {orderItems.length > 0 && <div className="space-y-3">{orderItems.map((order) => <div key={order.order_no} className="rounded-lg border border-morva-100 p-4"><div className="font-semibold">{order.order_no} — {order.order_type}</div><div className="mt-1 text-xs text-morva-600">تاریخ صدور: {date(order.issue_date)} | تاریخ اجرا: {date(order.effective_date)}</div><div className="mt-2 text-sm">{order.reason || 'بدون شرح ثبت‌شده'}</div>{order.legal_reference && <div className="mt-2 text-xs text-morva-500">مرجع: {order.legal_reference}</div>}</div>)}</div>}
      </section>

      {selectedPayslipId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedPayslipId(null); }}>
          <section aria-label="جزئیات فیش حقوقی" className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between gap-4"><h2 className="text-xl font-bold">جزئیات فیش حقوقی</h2><button type="button" aria-label="بستن" onClick={() => setSelectedPayslipId(null)} className="rounded-lg p-2 hover:bg-morva-100"><X size={20} /></button></div>
            {selectedPayslip.isLoading && <p className="text-sm text-morva-600">در حال دریافت جزئیات…</p>}
            {selectedPayslip.isError && <p role="alert" className="text-sm text-red-700">دریافت جزئیات فیش ناموفق بود.</p>}
            {detail && (
              <div className="space-y-5">
                <div className="grid gap-3 rounded-xl border border-morva-200 bg-morva-50 p-4 text-sm md:grid-cols-4">
                  <div><span className="text-morva-500">دوره</span><div className="font-semibold">{detail.period}</div></div>
                  <div><span className="text-morva-500">وضعیت</span><div className="font-semibold">{detail.status}</div></div>
                  <div><span className="text-morva-500">نسخه Rule Pack</span><div className="font-semibold">{detail.rule_pack_version}</div></div>
                  <div><span className="text-morva-500">خالص</span><div className="font-semibold">{money(detail.net)} {detail.currency_code}</div></div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm"><thead><tr className="border-b border-morva-200 text-right"><th className="px-3 py-2">ردیف</th><th className="px-3 py-2">عنوان</th><th className="px-3 py-2">مبلغ</th><th className="px-3 py-2">نوع</th><th className="px-3 py-2">توضیح</th></tr></thead><tbody>
                    {(detail.lines ?? []).map((line) => <tr key={`${line.sequence}-${line.code}`} className="border-b border-morva-100"><td className="px-3 py-2">{line.sequence}</td><td className="px-3 py-2 font-medium">{line.title}</td><td className="px-3 py-2">{money(line.amount)} {detail.currency_code}</td><td className="px-3 py-2">{line.kind}</td><td className="px-3 py-2">{line.explanation || 'بدون توضیح ثبت‌شده'}</td></tr>)}
                  </tbody></table>
                </div>
                <div className="grid gap-3 rounded-xl border border-morva-200 p-4 text-xs text-morva-700 md:grid-cols-2">
                  <div><div className="font-semibold">شناسه Snapshot</div><div className="mt-1 break-all">{detail.personnel_snapshot_id || 'ثبت نشده'}</div></div>
                  <div><div className="font-semibold">Hash Snapshot</div><div className="mt-1 break-all">{detail.personnel_snapshot_hash}</div></div>
                  <div><div className="font-semibold">Input Hash</div><div className="mt-1 break-all">{detail.input_hash || 'ثبت نشده'}</div></div>
                  <div><div className="font-semibold">Output Hash</div><div className="mt-1 break-all">{detail.output_hash}</div></div>
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default SelfService;
