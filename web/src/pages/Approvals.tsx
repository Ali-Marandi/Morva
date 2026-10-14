import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, Inbox, RefreshCw, XCircle } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import { useApprovals, useApprovalsStats } from "@/services";
import { DEMO_MODE } from "@/services/demo";
import type { ApiError, Approval } from "@/types/api";

type ApprovalFilter = "all" | Approval["status"];

const statusLabels: Record<Approval["status"], string> = {
  pending: "در انتظار",
  approved: "تأیید شده",
  rejected: "رد شده",
};

const statusStyles: Record<Approval["status"], string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
};

const typeLabels: Record<Approval["type"], string> = {
  payroll: "حقوق و دستمزد",
  expense: "هزینه",
  leave: "مرخصی",
  promotion: "ارتقا",
};

const formatNumber = (value: number) => new Intl.NumberFormat("fa-IR").format(value);

const formatDate = (value?: string) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("fa-IR").format(date);
};

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const candidate = error as Partial<ApiError> & { message?: string };
    return candidate.message || "دریافت اطلاعات درخواست‌ها ناموفق بود.";
  }
  return "دریافت اطلاعات درخواست‌ها ناموفق بود.";
}

function getApiResponseError(response: unknown): string | undefined {
  if (!response || typeof response !== "object" || !("success" in response) || response.success !== false) {
    return undefined;
  }

  if ("error" in response && response.error && typeof response.error === "object" && "message" in response.error) {
    const message = response.error.message;
    if (typeof message === "string" && message.trim()) return message;
  }

  return "دریافت اطلاعات درخواست‌ها ناموفق بود.";
}

const Approvals: React.FC = () => {
  const [filter, setFilter] = useState<ApprovalFilter>("all");
  const statsQuery = useApprovalsStats();
  const approvalsQuery = useApprovals({ page: 1, limit: 50, sort: "createdAt", order: "desc" });

  const isLoading = statsQuery.isLoading || approvalsQuery.isLoading;
  const queryError = statsQuery.isError ? statsQuery.error : approvalsQuery.isError ? approvalsQuery.error : undefined;
  const apiError = getApiResponseError(statsQuery.data) ?? getApiResponseError(approvalsQuery.data);
  const errorMessage = queryError ? getErrorMessage(queryError) : apiError;

  const stats = statsQuery.data?.success ? statsQuery.data.data : undefined;
  const approvals = approvalsQuery.data?.success ? approvalsQuery.data.data?.items ?? [] : [];
  const filteredApprovals = filter === "all" ? approvals : approvals.filter((item: Approval) => item.status === filter);

  const retry = () => {
    void statsQuery.refetch();
    void approvalsQuery.refetch();
  };

  return (
    <div className="space-y-6 p-4 md:p-8" dir="rtl">
      <header>
        <h1 className="text-3xl font-bold text-morva-900">صف تأییدها</h1>
        <p className="mt-2 text-morva-600">آمار و وضعیت درخواست‌ها از API سامانه دریافت می‌شود.</p>
      </header>

      {DEMO_MODE && (
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-900" role="note">
          محیط نمایشی مروا: اطلاعات نمونه است و هیچ تأیید یا رد واقعی انجام نمی‌شود.
        </div>
      )}

      <div className="rounded-xl border border-morva-200 bg-white p-4 text-sm leading-6 text-morva-700">
        این صفحه در حال حاضر فقط برای مشاهده است. عملیات تأیید و رد تا زمان تکمیل و اعتبارسنجی گردش کار مجاز، در رابط کاربری فعال نیست.
      </div>

      {isLoading && (
        <div className="rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700" role="status" aria-live="polite">
          در حال دریافت درخواست‌ها…
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
            className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold text-red-800 transition hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            <RefreshCw size={16} aria-hidden="true" />
            تلاش دوباره
          </button>
        </div>
      )}

      <section aria-label="آمار درخواست‌ها" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="در انتظار بررسی"
          value={stats ? formatNumber(stats.pendingCount) : "—"}
          icon={Clock3}
          trend={stats ? "در صف بررسی" : "داده موجود نیست"}
          color="orange"
        />
        <StatCard
          title="تأیید شده"
          value={stats ? formatNumber(stats.approvedCount) : "—"}
          icon={CheckCircle2}
          trend={stats ? "طبق آمار API" : "داده موجود نیست"}
          color="green"
        />
        <StatCard
          title="رد شده"
          value={stats ? formatNumber(stats.rejectedCount) : "—"}
          icon={XCircle}
          trend={stats ? "طبق آمار API" : "داده موجود نیست"}
          color="red"
        />
        <StatCard
          title="میانگین زمان بررسی"
          value={stats ? formatNumber(stats.averageApprovalTime) : "—"}
          icon={Inbox}
          trend={stats ? "ساعت" : "داده موجود نیست"}
          color="blue"
        />
      </section>

      <section className="overflow-hidden rounded-xl border border-morva-200 bg-white shadow-sm" aria-labelledby="approval-list-heading">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-morva-200 px-5 py-4">
          <div>
            <h2 id="approval-list-heading" className="text-lg font-bold text-morva-900">درخواست‌ها</h2>
            <p className="mt-1 text-sm text-morva-600">حداکثر ۵۰ درخواست اخیر</p>
          </div>
          <div className="flex flex-wrap gap-2" aria-label="فیلتر وضعیت درخواست">
            {([
              ["all", "همه"],
              ["pending", "در انتظار"],
              ["approved", "تأیید شده"],
              ["rejected", "رد شده"],
            ] as const).map(([status, label]) => (
              <button
                key={status}
                type="button"
                aria-pressed={filter === status}
                onClick={() => setFilter(status)}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-morva-500 focus:ring-offset-2 ${
                  filter === status
                    ? "border-morva-600 bg-morva-600 text-white"
                    : "border-morva-200 bg-white text-morva-700 hover:bg-morva-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {!isLoading && filteredApprovals.length === 0 && !errorMessage && (
          <div className="p-6 text-sm text-morva-700" role="status">
            {filter === "all" ? "هیچ درخواستی برای نمایش وجود ندارد." : "درخواستی با این وضعیت وجود ندارد."}
          </div>
        )}

        {filteredApprovals.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-morva-50 text-morva-700">
                <tr>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">نوع درخواست</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">شناسه مرجع</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">درخواست‌دهنده</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">مبلغ (ریال)</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">تاریخ ثبت</th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">وضعیت</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-morva-100">
                {filteredApprovals.map((item: Approval) => (
                  <tr key={item.id} className="hover:bg-morva-50">
                    <td className="whitespace-nowrap px-4 py-4 font-medium text-morva-900">{typeLabels[item.type]}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-morva-700">{item.referenceId}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-morva-700">{item.requestedBy}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-morva-700">{item.amount === undefined ? "—" : formatNumber(item.amount)}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-morva-600">{formatDate(item.createdAt)}</td>
                    <td className="whitespace-nowrap px-4 py-4">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[item.status]}`}>
                        {statusLabels[item.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Approvals;
