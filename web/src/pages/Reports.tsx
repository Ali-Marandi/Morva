import React from "react";
import { AlertCircle, FileText, RefreshCw } from "lucide-react";
import { useReports } from "@/services";
import type { ApiError, Report } from "@/types/api";

const reportTypeLabels: Record<Report["type"], string> = {
  payroll: "حقوق و دستمزد",
  tax: "مالیات",
  compliance: "انطباق",
  analytics: "تحلیلی",
};

const reportStatusLabels: Record<Report["status"], string> = {
  draft: "پیش‌نویس",
  generating: "در حال تولید",
  ready: "آماده",
  archived: "بایگانی‌شده",
};

const reportFormatLabels: Record<Report["format"], string> = {
  pdf: "PDF",
  excel: "Excel",
  csv: "CSV",
};

const statusClasses: Record<Report["status"], string> = {
  draft: "bg-gray-100 text-gray-700",
  generating: "bg-amber-100 text-amber-800",
  ready: "bg-emerald-100 text-emerald-800",
  archived: "bg-morva-100 text-morva-700",
};

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as Partial<ApiError> & { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return "دریافت فهرست گزارش‌ها ناموفق بود.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium" }).format(date);
}

const Reports: React.FC = () => {
  const reportsQuery = useReports({ page: 1, limit: 20 });
  const response = reportsQuery.data;
  const apiError = response && !response.success
    ? response.error?.message || "دریافت فهرست گزارش‌ها ناموفق بود."
    : undefined;
  const errorMessage = reportsQuery.isError
    ? getErrorMessage(reportsQuery.error)
    : apiError;
  const reports = response?.success ? response.data?.items ?? [] : [];

  const retry = () => {
    void reportsQuery.refetch();
  };

  return (
    <main className="min-h-full bg-gray-50 p-4 md:p-8" dir="rtl">
      <div className="mx-auto max-w-7xl space-y-6">
        <header>
          <h1 className="text-3xl font-bold text-morva-900">گزارش‌ها</h1>
          <p className="mt-2 text-morva-600">
            این صفحه سوابق گزارش‌های ثبت‌شده در سامانه را نمایش می‌دهد. تولید و دریافت فایل از این رابط فعال نیست.
          </p>
        </header>

        {reportsQuery.isLoading && (
          <div className="rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700" role="status" aria-live="polite">
            در حال دریافت فهرست گزارش‌ها…
          </div>
        )}

        {errorMessage && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              onClick={retry}
              disabled={reportsQuery.isFetching}
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-wait disabled:opacity-60"
            >
              <RefreshCw size={16} aria-hidden="true" className={reportsQuery.isFetching ? "animate-spin" : ""} />
              تلاش دوباره
            </button>
          </div>
        )}

        <section className="overflow-hidden rounded-xl border border-morva-200 bg-white shadow-sm" aria-labelledby="reports-list-heading">
          <div className="flex items-center gap-3 border-b border-morva-200 px-5 py-4">
            <FileText className="text-morva-700" aria-hidden="true" />
            <div>
              <h2 id="reports-list-heading" className="font-bold text-morva-900">سوابق گزارش</h2>
              <p className="mt-1 text-sm text-morva-600">حداکثر ۲۰ گزارش اخیر</p>
            </div>
          </div>

          {!reportsQuery.isLoading && !errorMessage && reports.length === 0 && (
            <p className="p-6 text-sm text-morva-700" role="status">
              گزارشی برای نمایش ثبت نشده است.
            </p>
          )}

          {reports.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-right text-morva-700">
                  <tr>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">نام گزارش</th>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">نوع</th>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">دوره</th>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">قالب</th>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">وضعیت</th>
                    <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">تاریخ ثبت</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-morva-100">
                  {reports.map((report: Report) => (
                    <tr key={report.id}>
                      <th scope="row" className="whitespace-nowrap px-4 py-3 text-right font-medium text-morva-900">{report.name}</th>
                      <td className="whitespace-nowrap px-4 py-3 text-morva-700">{reportTypeLabels[report.type]}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-morva-700">{report.period}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-morva-700">{reportFormatLabels[report.format]}</td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${statusClasses[report.status]}`}>
                          {reportStatusLabels[report.status]}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-morva-600">{formatDate(report.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
};

export default Reports;
