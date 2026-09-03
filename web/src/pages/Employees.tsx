import React from "react";
import StatCard from "@/components/ui/StatCard";
import { Users, UserPlus, AlertCircle } from "lucide-react";

interface EmployeeRecord {
  id: string;
  name: string;
  department: string;
  position: string;
  status: "active" | "inactive" | "suspended";
}

const Employees: React.FC = () => {
  const employees: EmployeeRecord[] = [
    {
      id: "EMP001",
      name: "علی محمدی",
      department: "فناوری اطلاعات",
      position: "مهندس ارشد",
      status: "active",
    },
    {
      id: "EMP002",
      name: "فاطمه احمدی",
      department: "منابع انسانی",
      position: "مدیر HR",
      status: "active",
    },
    {
      id: "EMP003",
      name: "حسن حسینی",
      department: "مالی",
      position: "حسابدار",
      status: "active",
    },
    {
      id: "EMP004",
      name: "نازنین رضایی",
      department: "بازاریابی",
      position: "مدیر بازار",
      status: "inactive",
    },
  ];

  const stats = {
    total: 42,
    active: 38,
    inactive: 3,
    suspended: 1,
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">مدیریت کارکنان</h1>
          <p className="text-gray-600 mt-2">مشاهده و مدیریت اطلاعات کارکنان</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="کل کارکنان"
            value={stats.total.toString()}
            icon={<Users className="w-8 h-8" />}
            trend="↑ ۲"
            color="blue"
          />
          <StatCard
            title="کارکنان فعال"
            value={stats.active.toString()}
            icon={<Users className="w-8 h-8" />}
            trend={`${((stats.active / stats.total) * 100).toFixed(1)}%`}
            color="green"
          />
          <StatCard
            title="کارکنان غیرفعال"
            value={stats.inactive.toString()}
            icon={<AlertCircle className="w-8 h-8" />}
            trend={`${((stats.inactive / stats.total) * 100).toFixed(1)}%`}
            color="orange"
          />
          <StatCard
            title="افزودن کارمند"
            value="+"
            icon={<UserPlus className="w-8 h-8" />}
            trend="جدید"
            color="indigo"
          />
        </div>

        {/* Employees Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">فهرست کارکنان</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    نام
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    بخش
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    سمت
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
                {employees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-right text-sm text-gray-900">
                      {emp.name}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {emp.department}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-600">
                      {emp.position}
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          emp.status === "active"
                            ? "bg-green-100 text-green-800"
                            : emp.status === "inactive"
                              ? "bg-gray-100 text-gray-800"
                              : "bg-red-100 text-red-800"
                        }`}
                      >
                        {emp.status === "active"
                          ? "فعال"
                          : emp.status === "inactive"
                            ? "غیرفعال"
                            : "تعلیق"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <button className="text-blue-600 hover:text-blue-900 font-medium">
                        ویرایش
                      </button>
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

export default Employees;
