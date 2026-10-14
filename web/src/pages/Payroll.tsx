import React from "react";
import { AlertCircle, CheckCircle2, Clock3, FileText, TrendingUp } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import { usePayrolls, usePayrollStats } from "@/services";
import type { ApiError, Payroll } from "@/types/api";

const formatNumber = (value: number) => new Intl.NumberFormat("fa-IR").format(value);

const formatDate = (value?: string) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("fa-IR").format(date);
};

const statusLabels: Record<Payroll["status"], string> = {
  draft: "پیش‌نویس",
  pending: "در انتظار تأیید",
  approved: "تأیید شده",
  processed: "پردازش شده",
  paid: "پرداخت شده",
};

const statusStyles: Record<Payroll["status"], string> = {
  draft: "bg-slate-100 text-slate-700",
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-sky-100 text-sky-800",
  processed: "bg-violet-100 text-violet-800",
  paid: "bg-emerald-100 text-emerald-800",
};

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const candidate = error as Partial<ApiError> & { message?: string };
    return candidate.message || "دریافت اطلاعات حقوق ناموفق بود.";
  }
  return "دریافت اطلاعات حقوق ناموفق بود.";
}

const Payroll: React.FC = () => {
  const statsQuery = usePayrollStats();
  const payrollsQuery = usePayrolls({ page: 1, limit: 50, order: "desc", sort: "createdAt" });

  const isLoading = statsQuery.isLoading || payrollsQuery.isLoading;
  const stats = statsQuery.data?.success ? statsQuery.data.data : undefined;
  const payrolls = payrollsQuery.data?.success ? payrollsQuery.data.data?.items ?? [] : [];
  const apiError = statsQuery.data && !statsQuery.data.success
    ? statsQuery.data.error
    : payrollsQuery.data && !payrollsQuery.data.success
      ? payrollsQuery.data.error
      : undefined;
  const error = statsQuery.error || payrollsQuery.error;
  const errorMessage = error ? getErrorMessage(error) : apiError?.message;

  const retry = () => {
    void statsQuery.refetch();
    void payrollsQuery.refetch();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8" dir="rtl">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">مدیریت حقوق</h1>
          <p className="mt-2 text-gray-600">خلاصه دوره‌ها و وضعیت پرداخت بر اساس اطلاعات دریافتی از API سامانه.</p>
        </header>

        {isLoading && (
          <div className="mb-6 rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700" role="status" aria-live="polite">
            در حال دریافت اطلاعات حقوق…
          </div>
        )}

        {errorMessage && (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              onClick={retry}
              className="rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold text-red-800 transition hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              تلاش دوباره
            </button>
          </div>
        )}

        <section aria-label="خلاصه حقوق و دستمزد" className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="تعداد دوره‌های حقوق"
            value={stats ? formatNumber(stats.totalPayrolls) : "—"}
            icon={FileText}
            trend={stats ? "دریافت‌شده از API" : "داده موجود نیست"}
            color="blue"
          />
          <StatCard
            title="مجموع مبالغ دوره‌ها"
            value={stats ? formatNumber(stats.totalAmount) : "—"}
            icon={TrendingUp}
            trend={stats ? "ریال" : "داده موجود نیست"}
            color="green"
          />
          <StatCard
            title="مبلغ در انتظار پرداخت"
            value={stats ? formatNumber(stats.pendingAmount) : "—"}
            icon={Clock3}
            trend={stats ? "ریال" : "داده موجود نیست"}
            color="orange"
          />
          <StatCard
            title="مبلغ پرداخت‌شده"
            value={stats ? formatNumber(stats.paidAmount) : "—"}
            icon={CheckCircle2}
            trend={stats ? `میانگین هر دوره: ${formatNumber(stats.averagePerPayroll)} ریال` : "داده موجود نیست"}
            color="emerald"
          />
        </section>

        <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm" aria-labelledby="recent-payrolls-heading">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 id="recent-payrolls-heading" className="text-xl font-bold text-gray-900">دوره‌های حقوق اخیر</h2>
            <p className="mt-1 text-sm text-gray-600">حداکثر ۵۰ دوره اخیر؛ وضعیت هر ردیف از پاسخ API گرفته می‌شود.</p>
          </div>

          {!isLoading && payrolls.length === 0 && !errorMessage && (
            <div className="p-6 text-sm text-gray-600" role="status">هیچ دوره حقوقی برای نمایش وجود ندارد.</div>
          )}

          {payrolls.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-right font-semibold text-gray-900">دوره</th>
                    <th scope="col" className="px-4 py-3 text-right font-semibold text-gray-900">تعداد کارکنان</th>
                    <th scope="col" className="px-4 py-3 text-right font-semibold text-gray-900">مبلغ کل (ریال)</th>
                    <th scope="col" className="px-4 py-3 text-right font-semibold text-gray-900">تاریخ پرداخت</th>
                    <th scope="col" className="px-4 py-3 text-right font-semibold text-gray-900">وضعیت</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {payrolls.map((payroll: Payroll) => (
                    <tr key={payroll.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-4 font-medium text-gray-900">{payroll.period}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-gray-700">{formatNumber(payroll.employeeCount)}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-gray-700">{formatNumber(payroll.totalAmount)}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-gray-700">{formatDate(payroll.payDate)}</td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[payroll.status]}`}>
                          {statusLabels[payroll.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <p className="mt-4 text-xs leading-6 text-gray-500">
          این صفحه صرفاً داده‌های دریافتی را نمایش می‌دهد و مجوز محاسبه نهایی یا پرداخت حقوق ایجاد نمی‌کند.
        </p>
      </div>
    </div>
  );
};

export default Payroll;
