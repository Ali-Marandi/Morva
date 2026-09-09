import React from "react";
import StatCard from "@/components/ui/StatCard";
import PayrollChart from "@/components/charts/PayrollChart";
import { BarChart3, TrendingUp, FileText } from "lucide-react";

interface ReportData {
  name: string;
  type: string;
  period: string;
  status: "ready" | "processing";
  generated: string;
}

const Reports: React.FC = () => {
  const reports: ReportData[] = [
    { name: "گزارش حقوق ماهیانه", type: "PDF", period: "آذر ۱۴۰۵", status: "ready", generated: "۱۴۰۵-۰۶-۱۵" },
    { name: "گزارش کسورات", type: "Excel", period: "آذر ۱۴۰۵", status: "ready", generated: "۱۴۰۵-۰۶-۱۵" },
    { name: "گزارش بیمه و تأمین‌اجتماعی", type: "PDF", period: "آذر ۱۴۰۵", status: "processing", generated: "—" },
    { name: "گزارش تجدید‌نظر حقوق", type: "Excel", period: "دی ۱۴۰۵", status: "ready", generated: "۱۴۰۵-۰۶-۱۴" },
  ];

  const chartData = [
    { month: "آذر", processed: 234, pending: 8, rejected: 3 },
    { month: "دی", processed: 240, pending: 5, rejected: 2 },
    { month: "بهمن", processed: 238, pending: 7, rejected: 3 },
    { month: "اسفند", processed: 245, pending: 3, rejected: 1 },
    { month: "فروردین", processed: 242, pending: 6, rejected: 2 },
  ];

  const stats = { totalReports: 24, thisMonth: 5, avgTime: "۲.۳ روز", successRate: "۹۸.۵%" };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">گزارش‌ها</h1>
          <p className="text-gray-600 mt-2">تولید و مدیریت گزارش‌های تحلیلی و مالی</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard title="کل گزارش‌ها" value={stats.totalReports.toString()} icon={FileText} trend={`+ ${stats.thisMonth} این ماه`} color="blue" />
          <StatCard title="میزان موفقیت" value={stats.successRate} icon={TrendingUp} trend="▲ ۱.۲%" color="green" />
          <StatCard title="میانگین زمان" value={stats.avgTime} icon={BarChart3} trend="▼ ۰.۳ روز" color="blue" />
          <StatCard title="گزارش درحال‌پردازش" value="۳" icon={FileText} trend="کاملاً سریع" color="orange" />
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">روند گزارش‌های ماهیانه</h2>
          <PayrollChart data={chartData} />
        </div>

        <div className="grid grid-cols-1 gap-4">
          {reports.map((report) => (
            <div key={`${report.name}-${report.period}`} className="bg-white rounded-lg shadow p-6 flex items-center justify-between hover:shadow-lg transition-shadow">
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900">{report.name}</h3>
                <div className="flex gap-4 mt-2 text-sm text-gray-600">
                  <span>دوره: {report.period}</span>
                  <span>نوع: {report.type}</span>
                  {report.generated !== "—" && <span>تاریخ: {report.generated}</span>}
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${report.status === "ready" ? "bg-green-100 text-green-800" : "bg-orange-100 text-orange-800"}`}>
                  {report.status === "ready" ? "آماده" : "درحال‌پردازش"}
                </span>
                <button
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${report.status === "ready" ? "bg-blue-100 text-blue-700 hover:bg-blue-200" : "bg-gray-100 text-gray-500 cursor-not-allowed"}`}
                  disabled={report.status !== "ready"}
                >
                  {report.status === "ready" ? "دانلود" : "در انتظار..."}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Reports;
