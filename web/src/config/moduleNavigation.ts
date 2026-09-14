import type { LucideIcon } from 'lucide-react';
import { BarChart3, BookOpenCheck, Calculator, FileBarChart, FileText, GraduationCap, Landmark, ReceiptText, Users, WalletCards } from 'lucide-react';

export interface ModuleItem {
  id: string;
  label: string;
  description?: string;
  children?: ModuleItem[];
}

export interface ModuleMenu extends ModuleItem {
  icon: LucideIcon;
}

export const moduleMenus: ModuleMenu[] = [
  {
    id: 'base', label: 'اطلاعات پایه', icon: BookOpenCheck,
    children: [
      { id: 'base-info', label: 'اطلاعات پایه', children: [{ id: 'tax-rates', label: 'درصد مالیات' }, { id: 'payment-locations', label: 'محل‌های پرداخت' }, { id: 'loan-types', label: 'انواع وام' }, { id: 'savings-types', label: 'انواع پس‌انداز' }] },
      { id: 'definitions', label: 'تعاریف', children: [{ id: 'benefits', label: 'مزایا' }, { id: 'deductions', label: 'کسور' }, { id: 'other-benefits', label: 'سایر مزایا' }, { id: 'employer-obligations', label: 'تعهدات کارفرما' }, { id: 'work-types', label: 'نوع کارکرد' }] },
    ],
  },
  {
    id: 'personnel', label: 'پرسنل', icon: Users,
    children: [
      { id: 'personnel-info', label: 'اطلاعات پرسنلی' }, { id: 'personnel-features', label: 'ویژگی‌های پرسنل' }, { id: 'personnel-assignments', label: 'تبعی پرسنل' }, { id: 'personnel-status', label: 'تاریخچه وضعیت پرسنل' }, { id: 'personnel-notifications', label: 'اطلاعات ایثارگری پرسنل' }, { id: 'personnel-bank', label: 'حساب بانکی پرسنل' }, { id: 'personnel-bank-2', label: 'حساب بانکی دوم پرسنل' }, { id: 'personnel-bank-status', label: 'وضعیت سپرده پرسنل' },
      { id: 'personnel-log', label: 'لاگ پرسنل', children: [{ id: 'personnel-entry', label: 'پرسنل ورودی' }, { id: 'personnel-exit', label: 'پرسنل خروجی' }] },
      { id: 'active-order', label: 'احکام فعال پرسنل', children: [{ id: 'set-active-order', label: 'تعیین حکم فعال پرسنل در ماه' }, { id: 'review-order', label: 'بررسی احکام درخواستی برای محاسبه' }] },
      { id: 'cartable-orders', label: 'دریافت احکام از سیستم کارگزینی', children: [{ id: 'employment-info', label: 'دریافت اطلاعات استخدامی پرسنل' }, { id: 'salary-orders', label: 'دریافت احکام حقوقی پرسنل' }, { id: 'form-control', label: 'کنترل فرم' }] },
    ],
  },
  {
    id: 'personnel-pay', label: 'حقوق پرسنل', icon: WalletCards,
    children: [
      { id: 'pay-factors', label: 'عوامل موثر بر حقوق', children: [{ id: 'benefits', label: 'مزایا' }, { id: 'deductions', label: 'کسور' }, { id: 'other-benefits', label: 'سایر مزایا' }, { id: 'employer-obligations', label: 'تعهدات کارفرما' }, { id: 'work-types', label: 'نوع کارکرد' }] },
      { id: 'pay-details', label: 'اطلاعات محاسبه حقوق' },
      { id: 'current-payroll', label: 'محاسبه جاری', children: [{ id: 'current-request', label: 'درخواست محاسبه' }, { id: 'current-results', label: 'نتایج محاسبه حقوق' }] },
      { id: 'deferred-payroll', label: 'محاسبه معوق', children: [{ id: 'deferred-request', label: 'درخواست محاسبه معوق' }, { id: 'deferred-results', label: 'نتایج محاسبه معوق' }] },
      { id: 'debt-payroll', label: 'محاسبه دیون', children: [{ id: 'debt-request', label: 'درخواست محاسبه دیون' }, { id: 'debt-results', label: 'نتایج محاسبه دیون' }] },
      { id: 'pay-request', label: 'درخواست وجه' }, { id: 'payslip', label: 'فیش حقوقی' }, { id: 'calculation-steps', label: 'مدیریت مراحل محاسبات' },
    ],
  },
  {
    id: 'teaching-pay', label: 'حق التدریس', icon: GraduationCap,
    children: [
      { id: 'teaching-data', label: 'اطلاعات محاسبه حق التدریس' },
      { id: 'teaching-operations', label: 'عملیات محاسبه', children: [{ id: 'teaching-orders', label: 'احکام حقوقی حق التدریس' }, { id: 'teaching-notices', label: 'ابلاغ‌های پرسنل' }, { id: 'teaching-corrections', label: 'کارکرد تعدیل پرسنل' }, { id: 'teaching-area-payment', label: 'منطقه پرداخت حق التدریس پرسنل' }] },
    ],
  },
  {
    id: 'reports', label: 'گزارش‌ها', icon: FileBarChart,
    children: [
      { id: 'personnel-reports', label: 'گزارشات پرسنل' }, { id: 'payroll-reports', label: 'گزارشات لیست حقوق' },
      { id: 'external-reports', label: 'گزارشات دیون', children: [{ id: 'external-payroll', label: 'گزارش لیست حقوق دیون' }, { id: 'external-supplementary', label: 'گزارش لیست بیمه تکمیلی دیون' }, { id: 'external-health', label: 'گزارش خدمات درمانی دیون' }, { id: 'external-payslip', label: 'گزارش فیش حقوق دیون' }, { id: 'external-files', label: 'فایل‌های خروجی سایر دستگاه‌های دیون' }, { id: 'external-orders', label: 'گزارش احکام برای دیون' }] },
      { id: 'loan-reports', label: 'گزارش وام‌ها' }, { id: 'social-insurance', label: 'گزارش لیست بیمه تامین اجتماعی' }, { id: 'tax-report', label: 'گزارش مالیات' }, { id: 'payslip-report', label: 'گزارش فیش حقوق' }, { id: 'bank-list-report', label: 'گزارش لیست بانک' }, { id: 'paya-report', label: 'گزارش پایا' }, { id: 'district-paya-report', label: 'گزارش پایا مناطق' }, { id: 'health-insurance-report', label: 'گزارش خدمات درمانی (ندا)' }, { id: 'supplementary-report', label: 'گزارش بیمه تکمیلی درمانی' }, { id: 'payment-code-report', label: 'گزارش ریز عوامل بر اساس کد پرداخت' }, { id: 'balance-report', label: 'گزارش موازنه حقوق' }, { id: 'taxon-report', label: 'گزارش ماهیت' }, { id: 'installment-report', label: 'گزارش کسر اقساط' }, { id: 'orders-list-report', label: 'گزارش لیست احکام' }, { id: 'payroll-control-report', label: 'گزارش کنترل اطلاعات پرسنل محاسبه حقوق' },
    ],
  },
  {
    id: 'report-requests', label: 'درخواست‌های گزارش', icon: ReceiptText,
    children: [{ id: 'report-request-list', label: 'فهرست درخواست‌های گزارش' }, { id: 'report-request-history', label: 'پیگیری و دریافت خروجی گزارش‌ها' }],
  },
];

export function findModuleItem(id: string): ModuleItem | undefined {
  const search = (items: ModuleItem[]): ModuleItem | undefined => {
    for (const item of items) {
      if (item.id === id) return item;
      const found = item.children && search(item.children);
      if (found) return found;
    }
    return undefined;
  };
  return search(moduleMenus);
}
