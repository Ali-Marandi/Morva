import React, { useState } from "react";
import StatCard from "@/components/ui/StatCard";
import { Settings, Lock, Bell, Database, Shield } from "lucide-react";

interface SettingGroup {
  name: string;
  description: string;
  icon: React.ReactNode;
  items: SettingItem[];
}

interface SettingItem {
  label: string;
  value: boolean | string;
}

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    notifications: true,
    emailNotifications: true,
    dataBackup: true,
    twoFactor: false,
    theme: "light",
  });

  const settingGroups: SettingGroup[] = [
    {
      name: "اطلاعیه‌ها",
      description: "مدیریت اطلاعیه‌های سیستم",
      icon: <Bell className="w-6 h-6" />,
      items: [
        {
          label: "اطلاعیه‌های درون‌برنامه",
          value: settings.notifications,
        },
        { label: "اطلاعیه‌های ایمیل", value: settings.emailNotifications },
      ],
    },
    {
      name: "امنیت",
      description: "تنظیمات امنیتی حساب",
      icon: <Shield className="w-6 h-6" />,
      items: [
        { label: "تأیید دورمرحله‌ای", value: settings.twoFactor },
      ],
    },
    {
      name: "داده‌ها",
      description: "مدیریت و بکاپ داده‌ها",
      icon: <Database className="w-6 h-6" />,
      items: [
        { label: "پشتیبان‌گیری خودکار", value: settings.dataBackup },
      ],
    },
  ];

  const stats = {
    lastBackup: "۱۴۰۵-۰۶-۱۵",
    accountAge: "۲ سال",
    securityScore: "۹۸/۱۰۰",
  };

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings((prev) => ({
      ...prev,
      [key]: typeof prev[key] === "boolean" ? !prev[key] : prev[key],
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">تنظیمات</h1>
          <p className="text-gray-600 mt-2">
            مدیریت تنظیمات سیستم و حساب کاربری
          </p>
        </div>

        {/* Security Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="امتیاز امنیتی"
            value={stats.securityScore}
            icon={<Shield className="w-8 h-8" />}
            trend="عالی"
            color="green"
          />
          <StatCard
            title="آخرین پشتیبان‌گیری"
            value={stats.lastBackup}
            icon={<Database className="w-8 h-8" />}
            trend="امروز"
            color="blue"
          />
          <StatCard
            title="عمر حساب"
            value={stats.accountAge}
            icon={<Lock className="w-8 h-8" />}
            trend="فعال"
            color="indigo"
          />
          <StatCard
            title="وضعیت سیستم"
            value="سالم"
            icon={<Settings className="w-8 h-8" />}
            trend="۱۰۰%"
            color="green"
          />
        </div>

        {/* Settings Groups */}
        <div className="space-y-6">
          {settingGroups.map((group, idx) => (
            <div key={idx} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-4">
                <div className="text-blue-600">{group.icon}</div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {group.name}
                  </h2>
                  <p className="text-sm text-gray-600">{group.description}</p>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {group.items.map((item, itemIdx) => (
                  <div
                    key={itemIdx}
                    className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg"
                  >
                    <span className="font-medium text-gray-900">
                      {item.label}
                    </span>
                    {typeof item.value === "boolean" && (
                      <button
                        onClick={() => {
                          if (item.label === "اطلاعیه‌های درون‌برنامه") {
                            toggleSetting("notifications");
                          } else if (item.label === "اطلاعیه‌های ایمیل") {
                            toggleSetting("emailNotifications");
                          } else if (item.label === "تأیید دورمرحله‌ای") {
                            toggleSetting("twoFactor");
                          } else if (item.label === "پشتیبان‌گیری خودکار") {
                            toggleSetting("dataBackup");
                          }
                        }}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          item.value ? "bg-green-600" : "bg-gray-300"
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            item.value ? "translate-x-6" : "translate-x-1"
                          }`}
                        />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Save Button */}
        <div className="mt-8 flex justify-end gap-4">
          <button className="px-6 py-2 border border-gray-300 text-gray-900 font-medium rounded-lg hover:bg-gray-50 transition-colors">
            انصراف
          </button>
          <button className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors">
            ذخیره تنظیمات
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
