import React, { useState } from 'react';
import { Send, MessageSquareText } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { selfService } from '@/services/self-service';

const statusLabel: Record<string, string> = {
  open: 'ثبت‌شده',
  under_review: 'در حال بررسی',
  resolved: 'حل‌شده',
  rejected: 'ردشده',
  closed: 'مختومه',
};

function Objections() {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState<'payroll' | 'personnel_order' | 'attendance' | 'deduction' | 'other'>('payroll');
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  const cases = useQuery({ queryKey: ['self', 'cases'], queryFn: () => selfService.getCases() });
  const createCase = useMutation({
    mutationFn: () => selfService.createCase({ category, priority, title, description }),
    onSuccess: () => {
      setTitle('');
      setDescription('');
      queryClient.invalidateQueries({ queryKey: ['self', 'cases'] });
    },
  });

  return (
    <div className="p-6 space-y-6" dir="rtl">
      <div><h1 className="text-3xl font-bold text-morva-900">اعتراض و پیگیری پرونده</h1><p className="text-morva-600 mt-2">هر درخواست با شناسه کارمند، وضعیت و سابقه ممیزی ثبت می‌شود.</p></div>

      <section className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4"><Send size={22} /><h2 className="text-lg font-bold">ثبت اعتراض / درخواست</h2></div>
        <div className="grid md:grid-cols-2 gap-4">
          <label className="text-sm">موضوع<select className="mt-1 w-full rounded-lg border p-2" value={category} onChange={(e) => setCategory(e.target.value as typeof category)}><option value="payroll">حقوق و دستمزد</option><option value="personnel_order">حکم پرسنلی</option><option value="attendance">حضور و غیاب</option><option value="deduction">کسورات</option><option value="other">سایر</option></select></label>
          <label className="text-sm">اولویت<select className="mt-1 w-full rounded-lg border p-2" value={priority} onChange={(e) => setPriority(e.target.value as typeof priority)}><option value="low">کم</option><option value="normal">عادی</option><option value="high">زیاد</option><option value="urgent">فوری</option></select></label>
          <label className="text-sm md:col-span-2">عنوان<input className="mt-1 w-full rounded-lg border p-2" value={title} onChange={(e) => setTitle(e.target.value)} /></label>
          <label className="text-sm md:col-span-2">شرح<textarea className="mt-1 w-full rounded-lg border p-2 min-h-32" value={description} onChange={(e) => setDescription(e.target.value)} /></label>
        </div>
        {createCase.isError && <p className="text-sm text-red-700 mt-3">ثبت درخواست ناموفق بود. اطلاعات احراز هویت و اتصال به پرونده پرسنلی را بررسی کنید.</p>}
        <button disabled={createCase.isPending || title.trim().length < 3 || description.trim().length < 10} onClick={() => createCase.mutate()} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-morva-600 px-4 py-2 text-white disabled:opacity-50"><Send size={17} />ثبت</button>
      </section>

      <section className="bg-white rounded-xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4"><MessageSquareText size={22} /><h2 className="text-lg font-bold">پرونده‌های من</h2></div>
        {cases.isLoading && <p className="text-sm text-morva-600">در حال دریافت…</p>}
        {cases.isError && <p className="text-sm text-red-700">دریافت پرونده‌ها ناموفق بود.</p>}
        {!cases.isLoading && !cases.isError && (cases.data?.data ?? []).length === 0 && <p className="text-sm text-morva-600">پرونده‌ای ثبت نشده است.</p>}
        {(cases.data?.data ?? []).map((item) => <article key={item.id} className="border-b border-morva-100 py-4 last:border-b-0"><div className="flex flex-wrap gap-2 items-center justify-between"><div className="font-semibold">{item.title}</div><span className="text-xs rounded-full bg-morva-50 px-3 py-1">{statusLabel[item.status] || item.status}</span></div><p className="text-sm text-morva-700 mt-2">{item.description}</p><div className="text-xs text-morva-500 mt-2">شناسه: {item.id} · ثبت: {new Date(item.submitted_at).toLocaleString('fa-IR')}</div>{item.resolution && <div className="mt-2 text-sm rounded-lg bg-morva-50 p-3">نتیجه: {item.resolution}</div>}</article>)}
      </section>
    </div>
  );
}

export default Objections;
