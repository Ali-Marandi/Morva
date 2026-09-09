import React from "react";
import { AlertCircle, Users } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import { useEmployeeStats, useEmployees } from "@/services";
import { ApiError, Employee } from "@/types/api";

const statusLabels: Record<Employee["status"], string> = {
  active: "فعال",
  inactive: "غیرفعال",
  "on-leave": "مرخصی",
};

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const candidate = error as Partial<ApiError> & { message?: string };
    return candidate.message || "دریافت اطلاعات کارکنان ناموفق بود.";
  }
  return "دریافت اطلاعات کارکنان ناموفق بود.";
}

const Employees: React.FC = () => {
  const statsQuery = useEmployeeStats();
  const employeesQuery = useEmployees({ page: 1, limit: 50, sort: "name", order: "asc" });
  const isLoading = statsQuery.isLoading || employeesQuery.isLoading;
  const error = statsQuery.error || employeesQuery.error;
  const stats = statsQuery.data?.success ? statsQuery.data.data : undefined;
  const employees = employeesQuery.data?.success ? employeesQuery.data.data?.items ?? [] : [];

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8" dir="rtl">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">مدیریت کارکنان</h1>
          <p className="text-gray-600 mt-2">فهرست و آمار کارکنان از API احراز‌شده سامانه دریافت می‌شود.</p>
        </div>

        {isLoading && (
          <div className="mb-6 rounded-xl border border-morva-200 bg-white p-4 text-sm text-morva-700">
            در حال دریافت اطلاعات کارکنان…
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
            {getErrorMessage(error)}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <StatCard
            title="کل کارکنان"
            value={stats ? new Intl.NumberFormat("fa-IR").format(stats.totalEmployees) : "—"}
            icon={Users}
            trend={stats ? `${new Intl.NumberFormat("fa-IR").format(stats.activeEmployees)} فعال` : "داده موجود نیست"}
            color="blue"
          />
          <StatCard
            title="کارکنان غیرفعال"
            value={stats ? new Intl.NumberFormat("fa-IR").format(stats.inactiveEmployees) : "—"}
            icon={AlertCircle}
            trend={stats ? `${new Intl.NumberFormat("fa-IR").format(stats.onLeaveEmployees)} در مرخصی` : "داده موجود نیست"}
            color="orange"
          />
          <StatCard
            title="جمع حقوق ماهانه"
            value={stats ? new Intl.NumberFormat("fa-IR").format(stats.totalPayroll) : "—"}
            icon={Users}
            trend={stats ? `میانگین ${new Intl.NumberFormat("fa-IR").format(stats.averageSalary)}` : "داده موجود نیست"}
            color="green"
          />
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">فهرست کارکنان</h2>
          </div>

          {!isLoading && employees.length === 0 && !error && (
            <div className="p-6 text-sm text-gray-600">هیچ رکوردی برای نمایش وجود ندارد.</div>
          )}

          {employees.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">نام</th>
                    <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">بخش</th>
                    <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">سمت</th>
                    <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">وضعیت</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {employees.map((employee: Employee) => (
                    <tr key={employee.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-right text-sm text-gray-900">{employee.name}</td>
                      <td className="px-6 py-4 text-right text-sm text-gray-600">{employee.department}</td>
                      <td className="px-6 py-4 text-right text-sm text-gray-600">{employee.position}</td>
                      <td className="px-6 py-4 text-right text-sm">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {statusLabels[employee.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Employees;
