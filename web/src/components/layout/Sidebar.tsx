import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { BarChart3, Users, FileText, Settings, HelpCircle, Menu, X, Database, CheckSquare, TrendingUp } from "lucide-react";

const navItems = [
  { name: "داشبورد", path: "/", icon: BarChart3 },
  { name: "پرونده کارکنان", path: "/employees", icon: Users },
  { name: "حقوق و دستمزد", path: "/payroll", icon: Database },
  { name: "فیش‌های حقوقی", path: "/payslips", icon: FileText },
  { name: "تأیید و مجوز", path: "/approvals", icon: CheckSquare },
  { name: "گزارش‌ها", path: "/reports", icon: TrendingUp },
  { name: "تنظیمات", path: "/settings", icon: Settings },
];

function Sidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 right-4 z-40 p-2 md:hidden bg-morva-600 text-white rounded-lg"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <aside
        className={`w-64 bg-white border-r border-morva-200 shadow-lg flex flex-col transition-all duration-300 fixed md:static md:translate-x-0 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        } h-screen z-30`}
        dir="rtl"
      >
        <div className="p-6 border-b border-morva-200">
          <h1 className="text-2xl font-bold text-morva-900 flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-morva-400 to-morva-600 rounded-lg flex items-center justify-center text-white font-bold">
              مروا
            </div>
            <span>Morva</span>
          </h1>
          <p className="text-xs text-morva-600 mt-2">سامانه حقوق و دستمزد</p>
        </div>

        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? "bg-morva-600 text-white shadow-md"
                    : "text-morva-700 hover:bg-morva-50"
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-morva-200 space-y-2">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-morva-700 hover:bg-morva-50 transition-all">
            <HelpCircle size={20} />
            <span className="font-medium">راهنما و پشتیبانی</span>
          </button>
          <p className="text-xs text-morva-600 text-center px-4">نسخه 1.0.0 | Enterprise</p>
        </div>
      </aside>

      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-20 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}

export default Sidebar;
