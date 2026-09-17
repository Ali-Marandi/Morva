/**
 * Service Layer Exports
 * Central export point for all services and hooks
 */

export { apiClient } from './api';
export type { ApiClient } from './api';

export { authService } from './auth';
export { employeeService } from './employees';
export { payrollService } from './payroll';
export { approvalService } from './approvals';
export { reportService } from './reports';
export { selfService } from './self-service';
export { importService } from './imports';
export { paymentExceptionService } from './payment-exceptions';
export type { ImportSource, ImportSummary, UploadResult } from './imports';

// React Query hooks
export {
  queryKeys,
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
  useApproveRequest,
  useRejectRequest,
  useApprovalsStats,
  useReports,
  useReport,
  useGenerateReport,
  useReportsStats,
} from './queries';
