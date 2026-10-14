import React from "react";
import { AlertCircle, CheckCircle2, RefreshCw, TrendingUp, Users } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import { useApprovalsStats, useEmployeeStats, usePayrolls, usePayrollStats } from "@/services";
import type { ApiError, Payroll } from "@/types/api";

const formatNumber = (value: number) => new Intl.NumberFormat("fa-IR").format(value);

const formatDate = (value: string) => {
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

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const candidate = error as Partial<ApiError> & { message?: string };
    return candidate.message || "دریافت داده از API ناموفق بود.";
  }
  return "دریافت داده از API ناموفق بود.";
}

function getApiResponseError(response: unknown): string | undefined {
  if (!response || typeof response !== "object" || !("success" in response) || response.success !== false) {
    return undefined;
  }

  if ("error" in response && response.error && typeof response.error === "object" && "message" in response.error) {
    const message = response.error.message;
    if (typeof message === "string" && message.trim()) return message;
  }

  return "دریافت داده از API ناموفق بود.";
}

function Dashboard() {
  const employeeStats = useEmployeeStats();
  const payrollStats = usePayrollStats();
  const approvalsStats = useApprovalsStats();
  const payrolls = usePayrolls({ page: 1, limit: 5, order: "desc", sort: "createdAt" });

  const queries = [employeeStats, payrollStats, approvalsStats, payrolls];
  const isLoading = queries.some((query) => query.isLoading);
  const queryError = queries.find((query) => query.isError)?.error;
  const apiError = queries
    .map((query) => getApiResponseError(query.data))
    .find((message): message is string => Boolean(message));
  const errorMessage = queryError ? getErrorMessage(queryError) : apiError;

  const employeeData = employeeStats.data?.success ? employeeStats.data.data : undefined;
  const payrollData = payrollStats.data?.success ? payrollStats.data.data : undefined;
  const approvalsData = approvalsStats.data?.success ? approvalsStats.data.data : undefined;
  const payrollItems = payrolls.data?.success ? (payrolls.data.data?.items ?? []) : [];

  const retry = () => {
    void employeeStats.refetch();
    void payrollStats.refetch();
    void approvalsStats.refetch();
    void payrolls.refetch();
  };

  return (
    <div className="space-y-6 p-6" dir="rtl">
      <header>
        <h1 className="text-3xl font-bold text-morva-900">داشبورد عملیاتی</h1>
        <p className="mt-2 text-morva-600">اطلاعات این صفحه فقط از APIهای سامانه دریافت می‌شود.</p>
      </header>

      {isLoading && (
        <div
          className="rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700"
          role="status"
          aria-live="polite"
        >
          در حال دریافت اطلاعات عملیاتی…
        </div>
      )}

      {errorMessage && (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          role="alert"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={retry}
            className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold text-red-800 transition hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            <RefreshCw size={16} aria-hidden="true" />
            تلاش دوباره
          </button>
        </div>
      )}

      <section aria-label="خلاصه وضعیت سامانه" className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="کل کارکنان"
          value={employeeData ? formatNumber(employeeData.totalEmployees) : "—"}
          icon={Users}
          trend={employeeData ? `${formatNumber(employeeData.activeEmployees)} فعال` : "داده موجود نیست"}
          color="blue"
        />
        <StatCard
          title="کل حقوق و دستمزد"
          value={payrollData ? formatNumber(payrollData.totalAmount) : "—"}
          icon={TrendingUp}
          trend={payrollData ? `${formatNumber(payrollData.totalPayrolls)} دوره` : "داده موجود نیست"}
          color="green"
        />
        <StatCard
          title="تأییدهای معلق"
          value={approvalsData ? formatNumber(approvalsData.pendingCount) : "—"}
          icon={AlertCircle}
          trend={approvalsData ? `${formatNumber(approvalsData.approvedCount)} تأییدشده` : "داده موجود نیست"}
          color="orange"
        />
        <StatCard
          title="پرداخت‌شده"
          value={payrollData ? formatNumber(payrollData.paidAmount) : "—"}
          icon={CheckCircle2}
          trend={payrollData ? `${formatNumber(payrollData.averagePerPayroll)} میانگین دوره` : "داده موجود نیست"}
          color="emerald"
        />
      </section>

      <section className="rounded-xl border border-morva-200 bg-white p-6 shadow-sm" aria-labelledby="recent-payrolls-heading">
        <div className="mb-4">
          <h2 id="recent-payrolls-heading" className="text-lg font-bold text-morva-900">آخرین دوره‌های حقوق</h2>
          <p className="mt-1 text-sm text-morva-600">فقط رکوردهای بازگشتی از API نمایش داده می‌شوند.</p>
        </div>

        {!isLoading && payrollItems.length === 0 && !errorMessage && (
          <div className="rounded-lg bg-morva-50 p-4 text-sm text-morva-700" role="status">
            هیچ دوره حقوقی برای نمایش وجود ندارد.
          </div>
        )}

        {payrollItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-morva-200 text-right text-morva-700">
                  <th scope="col" className="px-3 py-3 font-semibold">دوره</th>
                  <th scope="col" className="px-3 py-3 font-semibold">تعداد کارکنان</th>
                  <th scope="col" className="px-3 py-3 font-semibold">مبلغ (ریال)</th>
                  <th scope="col" className="px-3 py-3 font-semibold">وضعیت</th>
                  <th scope="col" className="px-3 py-3 font-semibold">تاریخ ایجاد</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-morva-100">
                {payrollItems.map((item: Payroll) => (
                  <tr key={item.id}>
                    <td className="px-3 py-3 font-medium text-morva-900">{item.period}</td>
                    <td className="px-3 py-3 text-morva-700">{formatNumber(item.employeeCount)}</td>
                    <td className="px-3 py-3 text-morva-700">{formatNumber(item.totalAmount)}</td>
                    <td className="px-3 py-3 text-morva-700">{statusLabels[item.status]}</td>
                    <td className="px-3 py-3 text-morva-600">{formatDate(item.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="text-xs leading-6 text-morva-600">
        این داشبورد صرفاً اطلاعات دریافتی را نمایش می‌دهد و مجوز محاسبه نهایی یا پرداخت حقوق ایجاد نمی‌کند.
      </p>
    </div>
  );
}

export default Dashboard;
