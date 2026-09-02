import React from "react";
import { TrendingUp, Users, AlertCircle, CheckCircle2 } from "lucide-react";
import StatCard from "../components/ui/StatCard";
import PayrollChart from "../components/charts/PayrollChart";

function Dashboard() {
  return (
    <div className="p-6 space-y-6" dir="rtl">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-morva-900">خوش‌آمدید به داشبورد</h1>
        <p className="text-morva-600 mt-2">وضعیت سامانه حقوق و دستمزد کارکنان آموزش‌وپرورش</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="پرونده‌های فعال"
          value="1,245"
          icon={Users}
          trend="+12%"
          color="blue"
        />
        <StatCard
          title="کل پرداخت‌ها"
          value="۵۲ میلیارد"
          icon={TrendingUp}
          trend="+8%"
          color="green"
        />
        <StatCard
          title="مغایرت‌های معلق"
          value="23"
          icon={AlertCircle}
          trend="-5%"
          color="orange"
        />
        <StatCard
          title="تأیید‌شده‌ها"
          value="98%"
          icon={CheckCircle2}
          trend="✓"
          color="emerald"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
          <h2 className="text-lg font-bold text-morva-900 mb-4">روند پرداخت‌های سه‌ماهه</h2>
          <PayrollChart />
        </div>

        <div className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
          <h3 className="text-lg font-bold text-morva-900 mb-4">وضعیت دوره‌ها</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-morva-50 rounded-lg">
              <span className="text-sm font-medium text-morva-900">1405-06</span>
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">تسویه شد</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-morva-50 rounded-lg">
              <span className="text-sm font-medium text-morva-900">1405-07</span>
              <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-bold rounded-full">محاسبه شد</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-morva-50 rounded-lg">
              <span className="text-sm font-medium text-morva-900">1405-08</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">ایجادشده</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-morva-900 mb-4">فعالیت‌های اخیر</h3>
        <div className="space-y-3">
          {[
            { action: "دوره ۱۴۰۵-۰۶ تسویه شد", time: "۲ ساعت پیش", status: "completed" },
            { action: "ثبت ۴۵ احکام جدید", time: "۴ ساعت پیش", status: "completed" },
            { action: "بازبینی گزارش مغایرت‌ها", time: "دیروز", status: "pending" },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 border-b border-morva-100 last:border-0">
              <div>
                <p className="text-sm font-medium text-morva-900">{item.action}</p>
                <p className="text-xs text-morva-600">{item.time}</p>
              </div>
              <div className={`w-2 h-2 rounded-full ${item.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500'}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
