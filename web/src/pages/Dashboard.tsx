import React from "react";
import { AlertCircle, CheckCircle2, TrendingUp, Users } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import { useApprovalsStats, useEmployeeStats, usePayrolls, usePayrollStats } from "@/services";
import { ApiError, Payroll } from "@/types/api";

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

function Dashboard() {
  const employeeStats = useEmployeeStats();
  const payrollStats = usePayrollStats();
  const approvalsStats = useApprovalsStats();
  const payrolls = usePayrolls({ page: 1, limit: 5, order: "desc", sort: "createdAt" });

  const queries = [employeeStats, payrollStats, approvalsStats, payrolls];
  const isLoading = queries.some((query) => query.isLoading);
  const firstError = queries.find((query) => query.isError)?.error;

  const employeeData = employeeStats.data?.success ? employeeStats.data.data : undefined;
  const payrollData = payrollStats.data?.success ? payrollStats.data.data : undefined;
  const approvalsData = approvalsStats.data?.success ? approvalsStats.data.data : undefined;
  const payrollItems = payrolls.data?.success ? (payrolls.data.data?.items ?? []) : [];

  return (
    <div className="p-6 space-y-6" dir="rtl">
      <div>
        <h1 className="text-3xl font-bold text-morva-900">داشبورد عملیاتی</h1>
        <p className="text-morva-600 mt-2">اطلاعات این صفحه فقط از APIهای احراز‌شده سامانه دریافت می‌شود.</p>
      </div>

      {isLoading && (
        <div className="rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700">در حال دریافت اطلاعات عملیاتی…</div>
      )}

      {firstError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{getErrorMessage(firstError)}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="کل کارکنان" value={employeeData ? formatNumber(employeeData.totalEmployees) : "—"} icon={Users} trend={employeeData ? `${formatNumber(employeeData.activeEmployees)} فعال` : "داده موجود نیست"} color="blue" />
        <StatCard title="کل حقوق و دستمزد" value={payrollData ? formatNumber(payrollData.totalAmount) : "—"} icon={TrendingUp} trend={payrollData ? `${formatNumber(payrollData.totalPayrolls)} دوره` : "داده موجود نیست"} color="green" />
        <StatCard title="تأییدهای معلق" value={approvalsData ? formatNumber(approvalsData.pendingCount) : "—"} icon={AlertCircle} trend={approvalsData ? `${formatNumber(approvalsData.approvedCount)} تأییدشده` : "داده موجود نیست"} color="orange" />
        <StatCard title="پرداخت‌شده" value={payrollData ? formatNumber(payrollData.paidAmount) : "—"} icon={CheckCircle2} trend={payrollData ? `${formatNumber(payrollData.averagePerPayroll)} میانگین دوره` : "داده موجود نیست"} color="emerald" />
      </div>

      <div className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-morva-900">آخرین دوره‌های حقوق</h2>
            <p className="text-sm text-morva-600 mt-1">فقط رکوردهای بازگشتی از API نمایش داده می‌شوند.</p>
          </div>
        </div>

        {!isLoading && payrollItems.length === 0 && !firstError && (
          <div className="rounded-lg bg-morva-50 p-4 text-sm text-morva-700">هیچ دوره حقوقی برای نمایش وجود ندارد.</div>
        )}

        {payrollItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-morva-200 text-right text-morva-700">
                  <th className="px-3 py-3 font-semibold">دوره</th>
                  <th className="px-3 py-3 font-semibold">تعداد کارکنان</th>
                  <th className="px-3 py-3 font-semibold">مبلغ</th>
                  <th className="px-3 py-3 font-semibold">وضعیت</th>
                  <th className="px-3 py-3 font-semibold">تاریخ ایجاد</th>
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
      </div>
    </div>
  );
}

export default Dashboard;
