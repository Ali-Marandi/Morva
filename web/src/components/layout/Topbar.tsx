import React from "react";
import { Bell, Settings, LogOut, User } from "lucide-react";

function Topbar() {
  return (
    <header className="bg-white border-b border-morva-200 px-6 py-4 flex justify-between items-center shadow-sm">
      <div className="flex-1">
        <h2 className="text-lg font-semibold text-morva-900">داشبورد</h2>
      </div>
      <div className="flex items-center gap-4">
        <button className="p-2 hover:bg-morva-100 rounded-lg transition-colors">
          <Bell size={20} className="text-morva-600" />
        </button>
        <button className="p-2 hover:bg-morva-100 rounded-lg transition-colors">
          <Settings size={20} className="text-morva-600" />
        </button>
        <div className="flex items-center gap-3 pl-4 border-r border-morva-200">
          <div className="text-right">
            <p className="text-sm font-medium text-morva-900">علی مرندی</p>
            <p className="text-xs text-morva-600">کارشناس مالی</p>
          </div>
          <div className="w-10 h-10 bg-gradient-to-br from-morva-400 to-morva-600 rounded-full flex items-center justify-center">
            <User size={20} className="text-white" />
          </div>
        </div>
        <button className="p-2 hover:bg-red-50 rounded-lg transition-colors text-red-600">
          <LogOut size={20} />
        </button>
      </div>
    </header>
  );
}

export default Topbar;
