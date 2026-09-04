import React, { useState } from "react";
import { Eye, EyeOff, ArrowLeft, ShieldCheck } from "lucide-react";

function Auth() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="min-h-screen bg-gradient-to-br from-morva-50 via-white to-morva-100 flex items-center justify-center p-4" dir="rtl">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-morva-400 to-morva-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <span className="text-white text-3xl font-bold">مروا</span>
          </div>
          <h1 className="text-3xl font-bold text-morva-900 mb-2">Morva</h1>
          <p className="text-morva-600">سامانه جامع حقوق و دستمزد</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl border border-morva-200 p-8 shadow-lg">
          <h2 className="text-2xl font-bold text-morva-900 mb-6 text-center">ورود به سامانه</h2>

          <form className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-morva-900 mb-2">ایمیل یا شماره کارمندی</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-morva-300 focus:border-morva-500 focus:ring-2 focus:ring-morva-500/20 transition-all text-morva-900"
                placeholder="example@edu.ir"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-morva-900 mb-2">رمز عبور</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-morva-300 focus:border-morva-500 focus:ring-2 focus:ring-morva-500/20 transition-all text-morva-900"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-morva-600 hover:text-morva-900 transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Remember & Forgot */}
            <div className="flex justify-between items-center text-sm">
              <label className="flex items-center gap-2 text-morva-700">
                <input type="checkbox" className="w-4 h-4 rounded accent-morva-600" />
                <span>مرا به خاطر داشته باش</span>
              </label>
              <a href="#" className="text-morva-600 hover:text-morva-700 font-medium">
                فراموشی رمز؟
              </a>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-morva-600 to-morva-700 text-white font-bold rounded-lg hover:shadow-lg transition-all mt-6 flex items-center justify-center gap-2"
            >
              <ShieldCheck size={20} />
              ورود ایمن
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-morva-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-morva-600">یا</span>
            </div>
          </div>

          {/* SSO Button */}
          <button
            type="button"
            className="w-full py-3 border border-morva-300 text-morva-700 font-medium rounded-lg hover:bg-morva-50 transition-all flex items-center justify-center gap-2"
          >
            <span>ورود با SSO/OIDC</span>
          </button>

          {/* Footer */}
          <p className="text-center text-xs text-morva-600 mt-6">
            احراز هویت شما تحت حفاظت MFA و رمزنگاری است.
          </p>
        </div>

        {/* Help Link */}
        <div className="text-center mt-6">
          <a href="#" className="text-morva-600 hover:text-morva-700 font-medium text-sm flex items-center justify-center gap-2">
            <ArrowLeft size={16} />
            نیاز به کمک دارید؟
          </a>
        </div>
      </div>
    </div>
  );
}

export default Auth;
