import React, { ChangeEvent, useCallback, useEffect, useState } from 'react';
import { FileSpreadsheet, Upload, RefreshCw, CheckCircle2, AlertCircle, Database } from 'lucide-react';
import { importService, ImportSource, ImportSummary } from '../services';

const supportedFiles = [
  'Prs Info.xlsx یا گزارش لیست پرسنل.xlsx',
  'گزارش لیست حقوق.xlsx',
  'گزارش احکام حقوقی.xlsx',
  'اکسل گزارش بیمه تکمیلی.xlsx',
  'گزارش بیمه خدمات درمانی.xlsx',
  'اکسل گزارش کسر اقساط.xlsx',
];

const number = (value: number) => new Intl.NumberFormat('fa-IR').format(value);

function Imports() {
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadSummary = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await importService.getSummary();
      if (!response.success || !response.data) throw new Error(response.error?.message || 'دریافت وضعیت واردسازی ناموفق بود.');
      setSummary(response.data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'ارتباط با سرور برقرار نشد.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void loadSummary(); }, [loadSummary]);

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setMessage('');
    setError('');
    setIsUploading(true);
    try {
      const response = await importService.upload(file);
      if (!response.success || !response.data) throw new Error(response.error?.message || 'واردسازی ناموفق بود.');
      setMessage(response.data.message);
      await loadSummary();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'امکان بارگذاری فایل وجود ندارد.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-6" dir="rtl">
      <div>
        <h1 className="text-3xl font-bold text-morva-900">واردسازی اطلاعات اکسل</h1>
        <p className="text-morva-600 mt-2">فایل‌ها در حافظهٔ محلی همین سامانه ذخیره می‌شوند. بارگذاری مجدد یک فایل، نسخهٔ قبلی همان فایل را جایگزین می‌کند.</p>
      </div>

      <section className="bg-white rounded-2xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 shrink-0 rounded-xl bg-morva-100 text-morva-700 flex items-center justify-center"><FileSpreadsheet size={25} /></div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-morva-900">انتخاب فایل</h2>
            <p className="text-sm text-morva-600 mt-1">فرمت مجاز: Excel با پسوند .xlsx، حداکثر ۲۵ مگابایت</p>
            <label className="mt-5 inline-flex items-center gap-2 rounded-lg bg-morva-600 px-4 py-3 text-white font-medium cursor-pointer hover:bg-morva-700 transition-colors">
              <Upload size={19} />
              {isUploading ? 'در حال واردسازی…' : 'انتخاب و واردسازی فایل'}
              <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="hidden" disabled={isUploading} onChange={handleFile} />
            </label>
          </div>
        </div>

        <div className="mt-6 rounded-xl bg-morva-50 p-4">
          <p className="font-medium text-morva-900">فایل‌های شناخته‌شده</p>
          <ul className="mt-3 grid gap-2 text-sm text-morva-700 md:grid-cols-2">
            {supportedFiles.map((file) => <li key={file}>• {file}</li>)}
          </ul>
        </div>

        {message && <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 size={18} />{message}</div>}
        {error && <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert"><AlertCircle size={18} />{error}</div>}
      </section>

      <section className="bg-white rounded-2xl border border-morva-200 p-6 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3"><Database className="text-morva-700" /><div><h2 className="text-lg font-bold text-morva-900">وضعیت داده‌های واردشده</h2><p className="text-sm text-morva-600">شمارش رکوردهای ذخیره‌شده در هر گروه</p></div></div>
          <button type="button" onClick={() => void loadSummary()} disabled={isLoading} className="p-2 rounded-lg text-morva-700 hover:bg-morva-50 disabled:opacity-50"><RefreshCw size={20} className={isLoading ? 'animate-spin' : ''} /></button>
        </div>

        {summary && <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(summary.categories).map(([key, label]) => <div key={key} className="rounded-xl border border-morva-200 p-4"><p className="text-sm text-morva-600">{label}</p><p className="mt-1 text-2xl font-bold text-morva-900">{number(summary.totals[key] || 0)}</p><p className="text-xs text-morva-600">رکورد</p></div>)}
        </div>}

        {summary && <ImportedFiles sources={summary.sources} />}
      </section>
    </div>
  );
}

function ImportedFiles({ sources }: { sources: ImportSource[] }) {
  if (!sources.length) return <p className="mt-6 rounded-lg bg-morva-50 p-4 text-sm text-morva-700">هنوز فایلی وارد نشده است.</p>;
  return <div className="mt-6 overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-morva-200 text-right text-morva-700"><th className="p-3">فایل</th><th className="p-3">گروه</th><th className="p-3">شیت</th><th className="p-3">تعداد ردیف</th><th className="p-3">آخرین واردسازی</th></tr></thead><tbody className="divide-y divide-morva-100">{sources.map((source) => <tr key={source.sourceKey}><td className="p-3 font-medium text-morva-900">{source.fileName}</td><td className="p-3 text-morva-700">{source.categoryLabel}</td><td className="p-3 text-morva-700">{source.sheetName}</td><td className="p-3 text-morva-700">{number(source.recordCount)}</td><td className="p-3 text-morva-600">{new Intl.DateTimeFormat('fa-IR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(source.importedAt))}</td></tr>)}</tbody></table></div>;
}

export default Imports;
