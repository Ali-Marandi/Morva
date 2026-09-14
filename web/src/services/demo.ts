import type { ApiResponse, Approval, ApprovalStats, Employee, EmployeeStats, PaginatedResponse, Payroll, PayrollStats, Report, ReportStats, User } from '../types/api';

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';
export const DEMO_LOGIN = 'demo@morva.local';
export const DEMO_PIN = 'demo';
export const DEMO_SESSION = 'morva-demo-session';
export const DEMO_SESSION_TTL = 24 * 60 * 60;
export const DEMO_USER_STORAGE_KEY = 'morva_demo_user';

export const demoUser: User = {
  id: 'demo-user',
  email: DEMO_LOGIN,
  name: 'کاربر نمایشی مروا',
  role: 'manager',
  department: 'محیط آزمایشی',
  permissions: ['demo:read'],
};

const employees: Employee[] = [
  { id: 'demo-employee-1', name: 'علی رضایی', email: 'ali.demo@morva.local', phone: '09120000001', department: 'آموزش', position: 'کارشناس', salary: 185000000, baseSalary: 150000000, benefits: 35000000, status: 'active', joinDate: '2023-01-15', lastPayDate: '2026-09-01', createdAt: '2026-01-01T08:00:00Z', updatedAt: '2026-09-01T08:00:00Z' },
  { id: 'demo-employee-2', name: 'سارا محمدی', email: 'sara.demo@morva.local', phone: '09120000002', department: 'فناوری اطلاعات', position: 'کارشناس ارشد', salary: 245000000, baseSalary: 205000000, benefits: 40000000, status: 'active', joinDate: '2022-05-10', lastPayDate: '2026-09-01', createdAt: '2026-01-01T08:00:00Z', updatedAt: '2026-09-01T08:00:00Z' },
];

const payrolls: Payroll[] = [
  { id: 'demo-payroll-1', period: '2026-09', payDate: '2026-09-30', status: 'approved', totalAmount: 4300000000, employeeCount: 24, createdBy: demoUser.id, createdAt: '2026-09-01T08:00:00Z', updatedAt: '2026-09-05T08:00:00Z' },
  { id: 'demo-payroll-2', period: '2026-08', payDate: '2026-08-31', status: 'paid', totalAmount: 4150000000, employeeCount: 24, createdBy: demoUser.id, createdAt: '2026-08-01T08:00:00Z', updatedAt: '2026-08-31T08:00:00Z', paidAt: '2026-08-31T12:00:00Z' },
];

const approvals: Approval[] = [
  { id: 'demo-approval-1', type: 'payroll', referenceId: payrolls[0].id, status: 'pending', requestedBy: demoUser.id, approverEmail: DEMO_LOGIN, notes: 'داده نمایشی برای بررسی گردش تأیید', createdAt: '2026-09-05T08:00:00Z', updatedAt: '2026-09-05T08:00:00Z', amount: 4300000000 },
];

const employeeStats: EmployeeStats = { totalEmployees: 24, activeEmployees: 22, inactiveEmployees: 1, onLeaveEmployees: 1, averageSalary: 192500000, totalPayroll: 4620000000 };
const payrollStats: PayrollStats = { totalPayrolls: 12, totalAmount: 48600000000, pendingAmount: 4300000000, paidAmount: 44300000000, averagePerPayroll: 4050000000 };
const approvalStats: ApprovalStats = { pendingCount: 1, approvedCount: 18, rejectedCount: 2, averageApprovalTime: 6.4 };
const reportStats: ReportStats = { totalReports: 37, reportsThisMonth: 5, averageGenerationTime: 2.7 };

const ok = <T,>(data: T): ApiResponse<T> => ({ success: true, data });
const page = <T,>(items: T[]): PaginatedResponse<T> => ({ items, total: items.length, page: 1, limit: items.length || 10, totalPages: 1 });

export function demoGet<T>(url: string): ApiResponse<T> | undefined {
  if (!DEMO_MODE) return undefined;
  const path = url.split('?')[0];
  if (path === '/auth/me') return ok(demoUser) as ApiResponse<T>;
  if (path === '/employees/stats') return ok(employeeStats) as ApiResponse<T>;
  if (path === '/payroll/stats') return ok(payrollStats) as ApiResponse<T>;
  if (path === '/approvals/stats') return ok(approvalStats) as ApiResponse<T>;
  if (path === '/reports/stats') return ok(reportStats) as ApiResponse<T>;
  if (path === '/employees') return ok(page(employees)) as ApiResponse<T>;
  if (path === '/payroll') return ok(page(payrolls)) as ApiResponse<T>;
  if (path === '/approvals') return ok(page(approvals)) as ApiResponse<T>;
  if (path === '/reports') return ok(page<Report>([])) as ApiResponse<T>;
  return ok([]) as ApiResponse<T>;
}

export function demoMutation<T>(): ApiResponse<T> | undefined {
  if (!DEMO_MODE) return undefined;
  return ok({} as T);
}
