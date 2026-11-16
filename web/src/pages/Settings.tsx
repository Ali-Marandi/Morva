import React from "react";
import { Bell, Database, Shield } from "lucide-react";

interface SettingGroup {
  name: string;
  description: string;
  icon: React.ReactNode;
  items: string[];
}

const settingGroups: SettingGroup[] = [
  {
    name: "اطلاعیه‌ها",
    description: "تنظیم شیوه دریافت اطلاعیه‌های سامانه",
    icon: <Bell className="h-6 w-6" aria-hidden="true" />,
    items: ["اطلاعیه‌های درون‌برنامه", "اطلاعیه‌های ایمیل"],
  },
  {
    name: "امنیت حساب",
    description: "مدیریت روش‌های محافظت از حساب کاربری",
    icon: <Shield className="h-6 w-6" aria-hidden="true" />,
    items: ["تأیید دومرحله‌ای"],
  },
  {
    name: "پشتیبان‌گیری",
    description: "مدیریت نسخه‌های پشتیبان اطلاعات",
    icon: <Database className="h-6 w-6" aria-hidden="true" />,
    items: ["پشتیبان‌گیری خودکار"],
  },
];

const Settings: React.FC = () => (
  <main className="min-h-screen bg-gray-50 p-4 md:p-8" dir="rtl">
    <div className="mx-auto max-w-7xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">تنظیمات</h1>
        <p className="mt-2 text-gray-600">اطلاع از گزینه‌های تنظیماتی سامانه</p>
      </header>

      <section className="mb-8 rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950" role="status" aria-live="polite">
        <h2 className="font-bold">ذخیره تنظیمات هنوز در دسترس نیست</h2>
        <p className="mt-2 text-sm leading-6">
          این گزینه‌ها هنوز به سرویس ذخیره‌سازی سامانه متصل نشده‌اند. در این صفحه چیزی تغییر یا ذخیره نمی‌شود؛ وضعیت پشتیبان‌گیری و امنیت حساب را از اینجا نمی‌توان بررسی کرد.
        </p>
      </section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {settingGroups.map((group) => (
          <section key={group.name} className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm" aria-labelledby={`settings-${group.name}`}>
            <header className="flex items-center gap-4 border-b border-gray-200 px-5 py-4">
              <div className="text-blue-700">{group.icon}</div>
              <div>
                <h2 id={`settings-${group.name}`} className="font-bold text-gray-900">{group.name}</h2>
                <p className="mt-1 text-sm text-gray-600">{group.description}</p>
              </div>
            </header>
            <ul className="divide-y divide-gray-100 px-5">
              {group.items.map((item) => (
                <li key={item} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <span className="font-medium text-gray-900">{item}</span>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">در دسترس نیست</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  </main>
);

export default Settings;
