/**
 * Custom Data Fetching Hooks for Pages
 * Combines React Query hooks with error handling and loading states
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import {
  useLogin,
  useLogout,
  useAuthMe,
  useEmployees,
  useEmployee,
  useCreateEmployee,
  useUpdateEmployee,
  useDeleteEmployee,
  useEmployeeStats,
  usePayrolls,
  usePayroll,
  useCreatePayroll,
  useProcessPayroll,
  useApprovePayroll,
  usePayrollStats,
  useApprovals,
  usePendingApprovals,
  useApproveRequest,
  useRejectRequest,
  useApprovalsStats,
  useReports,
  useReport,
  useGenerateReport,
  useReportsStats,
} from './services/queries';

// ============= Dashboard Hooks =============

export function useDashboardData() {
  const employeeStats = useEmployeeStats();
  const payrollStats = usePayrollStats();
  const approvalsStats = useApprovalsStats();
  const reportsStats = useReportsStats();
  
  const pendingApprovals = usePendingApprovals(undefined, {
    enabled: approvalsStats.isSuccess,
  });
  
  const isLoading =
    employeeStats.isLoading ||
    payrollStats.isLoading ||
    approvalsStats.isLoading ||
    reportsStats.isLoading;

  const isError =
    employeeStats.isError ||
    payrollStats.isError ||
    approvalsStats.isError ||
    reportsStats.isError;

  return {
    employeeStats: employeeStats.data?.data,
    payrollStats: payrollStats.data?.data,
    approvalsStats: approvalsStats.data?.data,
    reportsStats: reportsStats.data?.data,
    pendingApprovals: pendingApprovals.data?.data,
    isLoading,
    isError,
    error: isError
      ? employeeStats.error ||
        payrollStats.error ||
        approvalsStats.error ||
        reportsStats.error
      : null,
  };
}

// ============= Employees Page Hooks =============

export function useEmployeesPageData(filters: any = {}) {
  const employees = useEmployees(filters);
  const stats = useEmployeeStats();

  return {
    employees: employees.data?.data?.items || [],
    total: employees.data?.data?.total || 0,
    stats: stats.data?.data,
    isLoading: employees.isLoading || stats.isLoading,
    isError: employees.isError || stats.isError,
    error: employees.error || stats.error,
    refetch: () => {
      employees.refetch();
      stats.refetch();
    },
  };
}

export function useEmployeeForm() {
  const create = useCreateEmployee();
  const update = useUpdateEmployee;
  const delete_ = useDeleteEmployee;

  return {
    create,
    update,
    delete: delete_,
  };
}

// ============= Payroll Page Hooks =============

export function usePayrollPageData(filters: any = {}) {
  const payrolls = usePayrolls(filters);
  const stats = usePayrollStats();

  return {
    payrolls: payrolls.data?.data?.items || [],
    total: payrolls.data?.data?.total || 0,
    stats: stats.data?.data,
    isLoading: payrolls.isLoading || stats.isLoading,
    isError: payrolls.isError || stats.isError,
    error: payrolls.error || stats.error,
  };
}

export function usePayrollActions() {
  const create = useCreatePayroll();
  const process = useProcessPayroll();
  const approve = useApprovePayroll();

  return {
    create,
    process,
    approve,
  };
}

// ============= Approvals Page Hooks =============

export function useApprovalsPageData(filters: any = {}) {
  const approvals = useApprovals(filters);
  const pending = usePendingApprovals(filters);
  const stats = useApprovalsStats();

  return {
    allApprovals: approvals.data?.data?.items || [],
    pendingApprovals: pending.data?.data?.items || [],
    total: approvals.data?.data?.total || 0,
    stats: stats.data?.data,
    isLoading: approvals.isLoading || pending.isLoading || stats.isLoading,
    isError: approvals.isError || pending.isError || stats.isError,
    error: approvals.error || pending.error || stats.error,
  };
}

export function useApprovalActions() {
  const approve = useApproveRequest();
  const reject = useRejectRequest();

  return {
    approve,
    reject,
  };
}

// ============= Reports Page Hooks =============

export function useReportsPageData(filters: any = {}) {
  const reports = useReports(filters);
  const stats = useReportsStats();

  return {
    reports: reports.data?.data?.items || [],
    total: reports.data?.data?.total || 0,
    stats: stats.data?.data,
    isLoading: reports.isLoading || stats.isLoading,
    isError: reports.isError || stats.isError,
    error: reports.error || stats.error,
  };
}

export function useReportGeneration() {
  const generate = useGenerateReport();

  return {
    generate,
  };
}

// ============= Auth Hooks =============

export function useAuthActions() {
  const login = useLogin();
  const logout = useLogout();
  const me = useAuthMe();

  return {
    login,
    logout,
    me,
  };
}

// Re-export individual hooks for advanced usage
export {
  useLogin,
  useLogout,
  useAuthMe,
  useEmployees,
  useEmployee,
  useCreateEmployee,
  useUpdateEmployee,
  useDeleteEmployee,
  useEmployeeStats,
  usePayrolls,
  usePayroll,
  useCreatePayroll,
  useProcessPayroll,
  useApprovePayroll,
  usePayrollStats,
  useApprovals,
  usePendingApprovals,
  useApproveRequest,
  useRejectRequest,
  useApprovalsStats,
  useReports,
  useReport,
  useGenerateReport,
  useReportsStats,
};
