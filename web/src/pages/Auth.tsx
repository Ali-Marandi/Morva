import React, { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { authService, useLogin } from "../services";
import { DEMO_LOGIN, DEMO_MODE, DEMO_PIN } from "../services/demo";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "ورود انجام نشد. لطفاً اطلاعات را بررسی کنید و دوباره تلاش کنید.";
}

function Auth() {
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotMessage, setForgotMessage] = useState("");
  const [forgotError, setForgotError] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [formError, setFormError] = useState("");

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError("");
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !password) {
      setFormError("ایمیل سازمانی و رمز عبور را وارد کنید.");
      return;
    }
    try {
      const response = await loginMutation.mutateAsync({ email: normalizedEmail, password, rememberMe });
      if (!response?.success) {
        setFormError(response?.error?.message || "ایمیل یا رمز عبور صحیح نیست.");
        return;
      }
      navigate("/", { replace: true });
    } catch (error) {
      setFormError(getErrorMessage(error));
    }
  };

  const handleForgotPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setForgotMessage("");
    setForgotError("");
    const normalizedEmail = forgotEmail.trim();
    if (!normalizedEmail) {
      setForgotError("ایمیل سازمانی را وارد کنید.");
      return;
    }
    setForgotLoading(true);
    try {
      await authService.requestPasswordReset(normalizedEmail);
      setForgotMessage("اگر این ایمیل در سامانه ثبت شده باشد، راهنمای بازیابی رمز برای شما ارسال می‌شود.");
    } catch (error) {
      setForgotError(getErrorMessage(error));
    } finally {
      setForgotLoading(false);
    }
  };

  const useDemoAccount = () => {
    setEmail(DEMO_LOGIN);
    setPassword(DEMO_PIN);
    setFormError("");
    setShowForgotPassword(false);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-morva-50 via-white to-morva-100 px-4 py-8 sm:px-6" dir="rtl">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center justify-center">
        <div className="grid w-full overflow-hidden rounded-3xl border border-morva-200 bg-white shadow-xl lg:grid-cols-[0.9fr_1.1fr]">
          <aside className="relative hidden overflow-hidden bg-gradient-to-br from-morva-700 via-morva-800 to-morva-950 p-10 text-white lg:flex lg:flex-col lg:justify-between">
            <div className="absolute -left-20 -top-20 h-56 w-56 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
            <div className="absolute -bottom-24 -right-16 h-64 w-64 rounded-full bg-morva-400/20 blur-3xl" aria-hidden="true" />
            <div className="relative z-10">
              <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/15 text-2xl font-black shadow-lg ring-1 ring-white/20">مروا</div>
              <p className="mb-3 text-sm font-semibold text-white/70">سامانه جامع حقوق و دستمزد</p>
              <h1 className="max-w-sm text-4xl font-black leading-tight">ورود سریع، امن و مطمئن به مروا</h1>
              <p className="mt-5 max-w-md text-sm leading-7 text-white/75">مدیریت فرآیندهای منابع انسانی و حقوق و دستمزد با تمرکز بر امنیت، کنترل و قابلیت حسابرسی.</p>
            </div>
            <div className="relative z-10 space-y-4 text-sm text-white/80">
              <div className="flex items-center gap-3"><div className="rounded-full bg-white/10 p-2"><ShieldCheck size={17} /></div><span>احراز هویت امن و کنترل‌شده</span></div>
              <div className="flex items-center gap-3"><div className="rounded-full bg-white/10 p-2"><LockKeyhole size={17} /></div><span>حفاظت از نشست و اطلاعات حساب</span></div>
            </div>
          </aside>

          <section className="p-6 sm:p-10 lg:p-12">
            <div className="mx-auto w-full max-w-md">
              <div className="mb-8 text-center lg:text-right">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-morva-500 to-morva-700 text-xl font-black text-white shadow-lg lg:hidden">مروا</div>
                <p className="mb-2 text-sm font-semibold text-morva-600">خوش آمدید</p>
                <h2 className="text-3xl font-black tracking-tight text-morva-950">ورود به سامانه</h2>
                <p className="mt-2 text-sm leading-6 text-morva-600">برای ادامه، اطلاعات حساب سازمانی خود را وارد کنید.</p>
              </div>

              {DEMO_MODE && (
                <div className="mb-6 rounded-2xl border border-morva-200 bg-morva-50 p-4 text-sm text-morva-800">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-bold">حساب نمایشی</p>
                      <p className="mt-1 text-xs leading-5 text-morva-600">برای مشاهده رابط کاربری و داده‌های نمونه استفاده می‌شود و به سامانه واقعی متصل نیست.</p>
                    </div>
                    <button type="button" onClick={useDemoAccount} className="shrink-0 rounded-lg bg-morva-700 px-3 py-2 text-xs font-bold text-white transition hover:bg-morva-800">پر کردن خودکار</button>
                  </div>
                  <div className="mt-3 grid gap-1 rounded-xl bg-white/80 p-3 font-mono text-xs" dir="ltr">
                    <span>{DEMO_LOGIN}</span>
                    <span>{DEMO_PIN}</span>
                  </div>
                </div>
              )}

              {showForgotPassword ? (
                <div>
                  <button type="button" onClick={() => { setShowForgotPassword(false); setForgotMessage(""); setForgotError(""); }} className="mb-6 inline-flex items-center gap-2 text-sm font-semibold text-morva-700 transition-colors hover:text-morva-900">
                    <ArrowLeft size={16} /> بازگشت به ورود
                  </button>
                  <form onSubmit={handleForgotPassword} className="space-y-5" noValidate>
                    <div>
                      <label htmlFor="forgot-email" className="mb-2 block text-sm font-semibold text-morva-900">ایمیل سازمانی</label>
                      <div className="relative">
                        <Mail size={19} className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-morva-500" aria-hidden="true" />
                        <input id="forgot-email" type="email" inputMode="email" autoComplete="email" dir="ltr" value={forgotEmail} onChange={(event) => setForgotEmail(event.target.value)} className="w-full rounded-xl border border-morva-300 bg-white py-3.5 pr-11 pl-4 text-left text-morva-950 outline-none transition focus:border-morva-500 focus:ring-4 focus:ring-morva-500/10" placeholder="name@example.com" autoFocus required />
                      </div>
                    </div>
                    {forgotError && <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm leading-6 text-red-700"><AlertCircle className="mt-0.5 shrink-0" size={18} /><span>{forgotError}</span></div>}
                    {forgotMessage && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-sm leading-6 text-emerald-700">{forgotMessage}</div>}
                    <button type="submit" disabled={forgotLoading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-morva-700 py-3.5 font-bold text-white shadow-sm transition hover:bg-morva-800 focus:outline-none focus:ring-4 focus:ring-morva-500/20 disabled:cursor-not-allowed disabled:opacity-60">
                      {forgotLoading ? <Loader2 size={19} className="animate-spin" /> : <Mail size={19} />} ارسال راهنمای بازیابی
                    </button>
                  </form>
                </div>
              ) : (
                <form onSubmit={handleLogin} className="space-y-5" noValidate>
                  {formError && <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm leading-6 text-red-700"><AlertCircle className="mt-0.5 shrink-0" size={18} /><span>{formError}</span></div>}
                  <div>
                    <label htmlFor="login-email" className="mb-2 block text-sm font-semibold text-morva-900">ایمیل سازمانی</label>
                    <div className="relative">
                      <Mail size={19} className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-morva-500" aria-hidden="true" />
                      <input id="login-email" name="email" type="email" inputMode="email" autoComplete="username" dir="ltr" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-morva-300 bg-white py-3.5 pr-11 pl-4 text-left text-morva-950 outline-none transition focus:border-morva-500 focus:ring-4 focus:ring-morva-500/10" placeholder="name@example.com" required />
                    </div>
                  </div>
                  <div>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <label htmlFor="login-password" className="text-sm font-semibold text-morva-900">رمز عبور</label>
                      <button type="button" onClick={() => { setShowForgotPassword(true); setForgotEmail(email); setFormError(""); }} className="text-xs font-semibold text-morva-600 transition-colors hover:text-morva-800">رمز عبور را فراموش کرده‌اید؟</button>
                    </div>
                    <div className="relative">
                      <LockKeyhole size={19} className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-morva-500" aria-hidden="true" />
                      <input id="login-password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" dir="ltr" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-morva-300 bg-white py-3.5 pr-11 pl-12 text-left text-morva-950 outline-none transition focus:border-morva-500 focus:ring-4 focus:ring-morva-500/10" placeholder="••••••••" required />
                      <button type="button" aria-label={showPassword ? "مخفی کردن رمز عبور" : "نمایش رمز عبور"} aria-pressed={showPassword} onClick={() => setShowPassword((value) => !value)} className="absolute left-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-morva-500 transition hover:bg-morva-50 hover:text-morva-800 focus:outline-none focus:ring-2 focus:ring-morva-500/20">
                        {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                      </button>
                    </div>
                  </div>
                  <label className="flex cursor-pointer items-center gap-2.5 text-sm text-morva-700 select-none"><input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} className="h-4 w-4 rounded accent-morva-700" /><span>مرا در این دستگاه به خاطر بسپار</span></label>
                  <button type="submit" disabled={loginMutation.isPending} className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-morva-700 to-morva-800 py-3.5 font-bold text-white shadow-md transition hover:from-morva-800 hover:to-morva-900 focus:outline-none focus:ring-4 focus:ring-morva-500/20 disabled:cursor-not-allowed disabled:opacity-60">
                    {loginMutation.isPending ? <Loader2 size={19} className="animate-spin" /> : <ShieldCheck size={19} />} {loginMutation.isPending ? "در حال ورود..." : "ورود ایمن"}
                  </button>
                </form>
              )}
              <div className="mt-8 border-t border-morva-100 pt-6 text-center"><p className="text-xs leading-6 text-morva-500">احراز هویت حساب شما با سازوکارهای امنیتی سامانه محافظت می‌شود.<br />در صورت مشکل در ورود، با پشتیبانی سازمان خود تماس بگیرید.</p></div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default Auth;
