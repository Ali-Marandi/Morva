/**
 * React Query Hooks
 * Custom hooks for data fetching, caching, and mutations
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import {
  authService,
  employeeService,
  payrollService,
  approvalService,
  reportService,
} from '.';
import * as types from '../types/api';

// ============= Query Key Factory =============

export const queryKeys = {
  all: ['api'] as const,
  auth: () => [...queryKeys.all, 'auth'] as const,
  authMe: () => [...queryKeys.auth(), 'me'] as const,
  employees: () => [...queryKeys.all, 'employees'] as const,
  employeesList: (filters?: types.EmployeeFilters) => [...queryKeys.employees(), 'list', filters] as const,
  employeesStats: () => [...queryKeys.employees(), 'stats'] as const,
  employee: (id: string) => [...queryKeys.employees(), id] as const,
  payroll: () => [...queryKeys.all, 'payroll'] as const,
  payrollList: (filters?: types.PayrollFilters) => [...queryKeys.payroll(), 'list', filters] as const,
  payrollStats: () => [...queryKeys.payroll(), 'stats'] as const,
  payrollDetail: (id: string) => [...queryKeys.payroll(), id] as const,
  approvals: () => [...queryKeys.all, 'approvals'] as const,
  approvalsList: (filters?: any) => [...queryKeys.approvals(), 'list', filters] as const,
  approvalsStats: () => [...queryKeys.approvals(), 'stats'] as const,
  approval: (id: string) => [...queryKeys.approvals(), id] as const,
  reports: () => [...queryKeys.all, 'reports'] as const,
  reportsList: (filters?: any) => [...queryKeys.reports(), 'list', filters] as const,
  reportsStats: () => [...queryKeys.reports(), 'stats'] as const,
  report: (id: string) => [...queryKeys.reports(), id] as const,
};

// ============= Auth Hooks =============

export function useLogin(options?: UseMutationOptions<any, Error, types.LoginRequest>) {
  return useMutation({
    mutationFn: authService.login,
    ...options,
  });
}

export function useLogout(options?: UseMutationOptions<void, Error, void>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      queryClient.clear();
    },
    ...options,
  });
}

export function useAuthMe(options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.authMe(),
    queryFn: authService.getProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

// ============= Employee Hooks =============

export function useEmployees(
  filters?: types.EmployeeFilters,
  options?: UseQueryOptions<any>
) {
  return useQuery({
    queryKey: queryKeys.employeesList(filters),
    queryFn: () => employeeService.getAll(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
}

export function useEmployee(id: string, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.employee(id),
    queryFn: () => employeeService.getById(id),
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

export function useCreateEmployee(options?: UseMutationOptions<any, Error, types.CreateEmployeeDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: employeeService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.employeesList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.employeesStats() });
    },
    ...options,
  });
}

export function useUpdateEmployee(id: string, options?: UseMutationOptions<any, Error, types.UpdateEmployeeDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => employeeService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.employee(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.employeesList() });
    },
    ...options,
  });
}

export function useDeleteEmployee(id: string, options?: UseMutationOptions<void, Error, void>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => employeeService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.employeesList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.employeesStats() });
    },
    ...options,
  });
}

export function useEmployeeStats(options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.employeesStats(),
    queryFn: employeeService.getStats,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

// ============= Payroll Hooks =============

export function usePayrolls(
  filters?: types.PayrollFilters,
  options?: UseQueryOptions<any>
) {
  return useQuery({
    queryKey: queryKeys.payrollList(filters),
    queryFn: () => payrollService.getAll(filters),
    staleTime: 2 * 60 * 1000,
    ...options,
  });
}

export function usePayroll(id: string, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.payrollDetail(id),
    queryFn: () => payrollService.getById(id),
    staleTime: 3 * 60 * 1000,
    ...options,
  });
}

export function useCreatePayroll(options?: UseMutationOptions<any, Error, types.CreatePayrollDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: payrollService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.payrollList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.payrollStats() });
    },
    ...options,
  });
}

export function useProcessPayroll(options?: UseMutationOptions<any, Error, types.ProcessPayrollDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: payrollService.process,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.payrollList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.payrollStats() });
    },
    ...options,
  });
}

export function useApprovePayroll(options?: UseMutationOptions<any, Error, types.ApprovePayrollDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: payrollService.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.payrollList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalsStats() });
    },
    ...options,
  });
}

export function usePayrollStats(options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.payrollStats(),
    queryFn: payrollService.getStats,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

// ============= Approval Hooks =============

export function useApprovals(filters?: any, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.approvalsList(filters),
    queryFn: () => approvalService.getAll(filters),
    staleTime: 1 * 60 * 1000, // 1 minute (more frequent updates)
    ...options,
  });
}

export function usePendingApprovals(filters?: any, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: [...queryKeys.approvalsList(filters), 'pending'],
    queryFn: () => approvalService.getPending(filters),
    staleTime: 1 * 60 * 1000,
    ...options,
  });
}

export function useApproveRequest(options?: UseMutationOptions<any, Error, { approvalId: string; notes?: string }>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ approvalId, notes }) => approvalService.approve(approvalId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalsList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalsStats() });
    },
    ...options,
  });
}

export function useRejectRequest(options?: UseMutationOptions<any, Error, { approvalId: string; reason: string; notes?: string }>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ approvalId, reason, notes }) => approvalService.reject(approvalId, reason, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalsList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.approvalsStats() });
    },
    ...options,
  });
}

export function useApprovalsStats(options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.approvalsStats(),
    queryFn: approvalService.getStats,
    staleTime: 2 * 60 * 1000,
    ...options,
  });
}

// ============= Report Hooks =============

export function useReports(filters?: any, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.reportsList(filters),
    queryFn: () => reportService.getAll(filters),
    staleTime: 3 * 60 * 1000,
    ...options,
  });
}

export function useReport(id: string, options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.report(id),
    queryFn: () => reportService.getById(id),
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

export function useGenerateReport(options?: UseMutationOptions<any, Error, types.GenerateReportDto>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reportService.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reportsList() });
      queryClient.invalidateQueries({ queryKey: queryKeys.reportsStats() });
    },
    ...options,
  });
}

export function useReportsStats(options?: UseQueryOptions<any>) {
  return useQuery({
    queryKey: queryKeys.reportsStats(),
    queryFn: reportService.getStats,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}
