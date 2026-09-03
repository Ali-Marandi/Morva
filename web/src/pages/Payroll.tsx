import React from "react";
import StatCard from "@/components/ui/StatCard";
import PayrollChart from "@/components/charts/PayrollChart";
import { DollarSign, TrendingUp, AlertCircle } from "lucide-react";

interface PayrollRecord {
  month: string;
  processed: number;
  pending: number;
  rejected: number;
}

const Payroll: React.FC = () => {
  const payrollData: PayrollRecord[] = [
    { month: "آذر", processed: 38, pending: 2, rejected: 2 },
    { month: "دی", processed: 39, pending: 1, rejected: 2 },
    { month: "بهمن", processed: 40, pending: 1, rejected: 1 },
    { month: "اسفند", processed: 40, pending: 2, rejected: 0 },
    { month: "فروردین", processed: 38, pending: 3, rejected: 1 },
    { month: "اردیبهشت", processed: 39, pending: 2, rejected: 1 },
  ];

  const stats = {
    totalProcessed: 234,
    avgAmount: 45000000,
    pendingPayment: 850000000,
    monthlyGrowth: 2.5,
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">مدیریت حقوق</h1>
          <p className="text-gray-600 mt-2">نظارت و پردازش حقوق کارکنان</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="کل پرداخت‌ها"
            value={stats.totalProcessed.toString()}
            icon={<DollarSign className="w-8 h-8" />}
            trend="▲ ۳.۲%"
            color="green"
          />
          <StatCard
            title="میانگین حقوق"
            value={`${(stats.avgAmount / 1000000).toFixed(1)}M`}
            icon={<TrendingUp className="w-8 h-8" />}
            trend="▲ ۲.۵%"
            color="blue"
          />
          <StatCard
            title="در انتظار پرداخت"
            value={`${(stats.pendingPayment / 1000000000).toFixed(2)}B`}
            icon={<AlertCircle className="w-8 h-8" />}
            trend="▼ ۱.۸%"
            color="orange"
          />
          <StatCard
            title="رشد ماهیانه"
            value={`${stats.monthlyGrowth.toFixed(1)}%`}
            icon={<TrendingUp className="w-8 h-8" />}
            trend="▲ ۰.۵%"
            color="indigo"
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              روند پرداخت ماهیانه
            </h2>
            <PayrollChart data={payrollData} />
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              خلاصه وضعیت
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <span className="font-semibold text-green-900">تکمیل‌شده</span>
                <span className="text-2xl font-bold text-green-600">۲۳۴</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg">
                <span className="font-semibold text-orange-900">
                  در انتظار
                </span>
                <span className="text-2xl font-bold text-orange-600">۲۵</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                <span className="font-semibold text-red-900">رد‌شده</span>
                <span className="text-2xl font-bold text-red-600">۱۲</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Payroll Cycles */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">
              دوره‌های حقوق اخیر
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    ماه
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    تکمیل‌شده
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    در انتظار
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    رد‌شده
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    وضعیت
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {payrollData.map((record, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-right text-sm font-medium text-gray-900">
                      {record.month}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {record.processed}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {record.pending}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {record.rejected}
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        تکمیل
                      </span>
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

export default Payroll;
