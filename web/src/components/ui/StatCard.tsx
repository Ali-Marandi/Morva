import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  trend?: string;
  color?: "blue" | "green" | "orange" | "emerald" | "red";
}

const colorClasses = {
  blue: "bg-blue-50 text-blue-600",
  green: "bg-green-50 text-green-600",
  orange: "bg-orange-50 text-orange-600",
  emerald: "bg-emerald-50 text-emerald-600",
  red: "bg-red-50 text-red-600",
};

function StatCard({ title, value, icon: Icon, trend, color = "blue" }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm hover:shadow-md transition-all">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-sm text-morva-600 mb-1">{title}</p>
          <p className="text-2xl font-bold text-morva-900">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon size={24} />
        </div>
      </div>
      {trend && (
        <div className={`text-sm font-medium ${trend.startsWith('+') ? 'text-green-600' : trend.startsWith('-') ? 'text-red-600' : 'text-green-600'}`}>
          {trend}
        </div>
      )}
    </div>
  );
}

export default StatCard;
