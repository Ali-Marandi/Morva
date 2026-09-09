import React from 'react';
import { FileText, Download, BriefcaseBusiness, UserRound } from 'lucide-react';
import { selfService } from '@/services/self-service';
import { useQuery } from '@tanstack/react-query';

const money = (value: string) => new Intl.NumberFormat('fa-IR').format(Number(value));

function SelfService() {
  const profile = useQuery({ queryKey: ['self', 'profile'], queryFn: selfService.getProfile });
  const payslips = useQuery({ queryKey: ['self', 'payslips'], queryFn: () => selfService.getPayslips() });
  const orders = useQuery({ queryKey: ['self', 'orders'], queryFn: selfService.getOrders });

  const downloadPdf = async (artifactId: string, period: string) => {
    const response = await selfService.getPayslipPdf(artifactId);
    const blob = response instanceof Blob ? response : new Blob([response as BlobPart]);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `payslip-${period}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const profileData = profile.data?.data;
  const payslipItems = payslips.data?.data ?? [];
  const orderItems = orders.data?.data ?? [];

  return (
    <div className="p-6 space-y-6" dir="rtl">
      <div>
        <h1 className="text-3xl font-bold text-morva-900">خدمات کارکنان</h1>
        <p className="text-morva-600 mt-2">نمایش اطلاعات شخصی، فیش حقوقی و احکام فقط از مسیر احراز‌شده سامانه.</p>
      </div>

      {profile.isError && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">دریافت پروفایل ناموفق بود.</div>}
      {profileData && (
        <section className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4"><UserRound size={22} /><h2 className="text-lg font-bold">پروفایل پرسنلی</h2></div>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div><span className="text-morva-500">نام</span><div className="font-semibold mt-1">{profileData.first_name} {profileData.last_name}</div></div>
            <div><span className="text-morva-500">کد کارمند</span><div className="font-semibold mt-1">{profileData.employee_no}</div></div>
            <div><span className="text-morva-500">وضعیت</span><div className="font-semibold mt-1">{profileData.status}</div></div>
          </div>
        </section>
      )}

      <section className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4"><FileText size={22} /><h2 className="text-lg font-bold">فیش‌های حقوقی</h2></div>
        {payslips.isLoading && <p className="text-sm text-morva-600">در حال دریافت…</p>}
        {payslips.isError && <p className="text-sm text-red-700">دریافت فیش‌ها ناموفق بود.</p>}
        {!payslips.isLoading && !payslips.isError && payslipItems.length === 0 && <p className="text-sm text-morva-600">فیش قابل نمایش وجود ندارد.</p>}
        {payslipItems.length > 0 && (
          <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-morva-200 text-right"><th className="px-3 py-3">دوره</th><th className="px-3 py-3">ناخالص</th><th className="px-3 py-3">کسورات</th><th className="px-3 py-3">خالص</th><th className="px-3 py-3">عملیات</th></tr></thead><tbody>
            {payslipItems.map((item) => <tr key={item.artifact_id} className="border-b border-morva-100"><td className="px-3 py-3">{item.period}</td><td className="px-3 py-3">{money(item.gross)}</td><td className="px-3 py-3">{money(item.deductions)}</td><td className="px-3 py-3 font-semibold">{money(item.net)}</td><td className="px-3 py-3"><button onClick={() => downloadPdf(item.artifact_id, item.period)} className="inline-flex items-center gap-2 rounded-lg bg-morva-600 px-3 py-2 text-white hover:bg-morva-700"><Download size={16} /> PDF</button></td></tr>)}
          </tbody></table></div>
        )}
      </section>

      <section className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4"><BriefcaseBusiness size={22} /><h2 className="text-lg font-bold">احکام پرسنلی</h2></div>
        {orders.isLoading && <p className="text-sm text-morva-600">در حال دریافت…</p>}
        {orders.isError && <p className="text-sm text-red-700">دریافت احکام ناموفق بود.</p>}
        {!orders.isLoading && !orders.isError && orderItems.length === 0 && <p className="text-sm text-morva-600">حکم قابل نمایش وجود ندارد.</p>}
        {orderItems.length > 0 && <div className="space-y-3">{orderItems.map((order) => <div key={order.order_no} className="rounded-lg border border-morva-100 p-4"><div className="font-semibold">{order.order_no} — {order.order_type}</div><div className="text-xs text-morva-600 mt-1">تاریخ اجرا: {order.effective_date}</div><div className="text-sm mt-2">{order.reason || 'بدون شرح ثبت‌شده'}</div></div>)}</div>}
      </section>
    </div>
  );
}

export default SelfService;
