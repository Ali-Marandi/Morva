import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-morva-50 to-white flex items-center justify-center p-4" dir="rtl">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-morva-900 mb-4">۴۰۴</h1>
        <h2 className="text-3xl font-bold text-morva-700 mb-2">صفحه‌ای یافت نشد</h2>
        <p className="text-morva-600 text-lg mb-8">متأسفانه صفحه‌ای که دنبال آن می‌گردید وجود ندارد.</p>
        
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-morva-600 text-white font-bold rounded-lg hover:bg-morva-700 transition-all"
        >
          <ArrowRight size={20} />
          بازگشت به داشبورد
        </Link>
      </div>
    </div>
  );
}

export default NotFound;
