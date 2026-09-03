import React, { useState } from "react";
import StatCard from "@/components/ui/StatCard";
import { CheckCircle, Clock, XCircle, Inbox } from "lucide-react";

interface ApprovalRequest {
  id: string;
  type: string;
  employee: string;
  amount?: string;
  status: "pending" | "approved" | "rejected";
  date: string;
}

const Approvals: React.FC = () => {
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");

  const requests: ApprovalRequest[] = [
    {
      id: "APR001",
      type: "درخواست مرخصی",
      employee: "علی محمدی",
      status: "pending",
      date: "۱۴۰۵-۰۶-۱۵",
    },
    {
      id: "APR002",
      type: "درخواست پاداش",
      employee: "فاطمه احمدی",
      amount: "۵،۰۰۰،۰۰۰",
      status: "approved",
      date: "۱۴۰۵-۰۶-۱۴",
    },
    {
      id: "APR003",
      type: "افزایش حقوق",
      employee: "حسن حسینی",
      status: "pending",
      date: "۱۴۰۵-۰۶-۱۳",
    },
    {
      id: "APR004",
      type: "تغییر پوسیشن",
      employee: "نازنین رضایی",
      status: "rejected",
      date: "۱۴۰۵-۰۶-۱۲",
    },
    {
      id: "APR005",
      type: "درخواست مرخصی",
      employee: "محمد علیپور",
      status: "approved",
      date: "۱۴۰۵-۰۶-۱۱",
    },
  ];

  const stats = {
    pending: 8,
    approved: 15,
    rejected: 2,
    total: 25,
  };

  const filteredRequests =
    filter === "all"
      ? requests
      : requests.filter((req) => req.status === filter);

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">تأیید و بررسی</h1>
          <p className="text-gray-600 mt-2">
            مدیریت درخواست‌های تأیید و بررسی مستندات
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="کل درخواست‌ها"
            value={stats.total.toString()}
            icon={<Inbox className="w-8 h-8" />}
            trend="↑ ۳"
            color="blue"
          />
          <StatCard
            title="در انتظار تأیید"
            value={stats.pending.toString()}
            icon={<Clock className="w-8 h-8" />}
            trend={`${((stats.pending / stats.total) * 100).toFixed(0)}%`}
            color="orange"
          />
          <StatCard
            title="تأیید‌شده"
            value={stats.approved.toString()}
            icon={<CheckCircle className="w-8 h-8" />}
            trend={`${((stats.approved / stats.total) * 100).toFixed(0)}%`}
            color="green"
          />
          <StatCard
            title="رد‌شده"
            value={stats.rejected.toString()}
            icon={<XCircle className="w-8 h-8" />}
            trend={`${((stats.rejected / stats.total) * 100).toFixed(0)}%`}
            color="red"
          />
        </div>

        {/* Filter Buttons */}
        <div className="flex flex-wrap gap-2 mb-8">
          {(["all", "pending", "approved", "rejected"] as const).map(
            (status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  filter === status
                    ? status === "pending"
                      ? "bg-orange-100 text-orange-700"
                      : status === "approved"
                        ? "bg-green-100 text-green-700"
                        : status === "rejected"
                          ? "bg-red-100 text-red-700"
                          : "bg-blue-100 text-blue-700"
                    : "bg-white text-gray-700 border border-gray-200"
                }`}
              >
                {status === "all"
                  ? "همه"
                  : status === "pending"
                    ? "در انتظار"
                    : status === "approved"
                      ? "تأیید‌شده"
                      : "رد‌شده"}
              </button>
            )
          )}
        </div>

        {/* Requests Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">
              درخواست‌های تأیید
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    نوع درخواست
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    نام کارمند
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    مبلغ
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    تاریخ
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    وضعیت
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    عملیات
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-right text-sm text-gray-900">
                      {req.type}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {req.employee}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {req.amount || "—"}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {req.date}
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          req.status === "pending"
                            ? "bg-orange-100 text-orange-800"
                            : req.status === "approved"
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                        }`}
                      >
                        {req.status === "pending"
                          ? "در انتظار"
                          : req.status === "approved"
                            ? "تأیید‌شده"
                            : "رد‌شده"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      {req.status === "pending" && (
                        <div className="flex gap-2">
                          <button className="text-green-600 hover:text-green-900 font-medium">
                            تأیید
                          </button>
                          <button className="text-red-600 hover:text-red-900 font-medium">
                            رد
                          </button>
                        </div>
                      )}
                      {req.status !== "pending" && (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Approvals;
