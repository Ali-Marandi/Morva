/**
 * API Type Definitions
 * Central source of truth for all API contracts
 */

// Generic API response wrapper
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: {
    timestamp: string;
    version: string;
  };
}

// Error structure
export interface ApiError {
  code: string;
  message: string;
  statusCode: number;
  details?: Record<string, unknown>;
}

// Pagination
export interface PaginationParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// ============= Auth Types =============

export interface LoginRequest {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'employee';
  department?: string;
  avatar?: string;
  permissions: string[];
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface RefreshTokenResponse {
  accessToken: string;
  expiresIn: number;
}

// ============= Employee Types =============

export interface Employee {
  id: string;
  name: string;
  email: string;
  phone: string;
  department: string;
  position: string;
  salary: number;
  baseSalary: number;
  benefits: number;
  status: 'active' | 'inactive' | 'on-leave';
  joinDate: string;
  lastPayDate?: string;
  taxId?: string;
  bankAccount?: string;
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateEmployeeDto {
  name: string;
  email: string;
  phone: string;
  department: string;
  position: string;
  baseSalary: number;
  benefits?: number;
  joinDate: string;
  taxId?: string;
  bankAccount?: string;
}

export interface UpdateEmployeeDto {
  name?: string;
  email?: string;
  phone?: string;
  department?: string;
  position?: string;
  baseSalary?: number;
  benefits?: number;
  status?: 'active' | 'inactive' | 'on-leave';
  taxId?: string;
  bankAccount?: string;
}

export interface EmployeeFilters extends PaginationParams {
  department?: string;
  status?: 'active' | 'inactive' | 'on-leave';
  search?: string;
}

export interface EmployeeStats {
  totalEmployees: number;
  activeEmployees: number;
  inactiveEmployees: number;
  onLeaveEmployees: number;
  averageSalary: number;
  totalPayroll: number;
}

// ============= Payroll Types =============

export interface Payroll {
  id: string;
  period: string; // YYYY-MM format
  payDate: string;
  status: 'draft' | 'pending' | 'approved' | 'processed' | 'paid';
  totalAmount: number;
  employeeCount: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  approvedBy?: string;
  approvedAt?: string;
  processedAt?: string;
  paidAt?: string;
}

export interface PayrollDetail {
  id: string;
  payrollId: string;
  employeeId: string;
  employeeName: string;
  baseSalary: number;
  benefits: number;
  deductions: number;
  tax: number;
  netSalary: number;
  overtimePay?: number;
  bonusAmount?: number;
  description?: string;
}

export interface CreatePayrollDto {
  period: string;
  payDate: string;
  employeeIds: string[];
}

export interface ProcessPayrollDto {
  payrollId: string;
  notes?: string;
}

export interface ApprovePayrollDto {
  payrollId: string;
  approvedBy: string;
  notes?: string;
}

export interface PayrollFilters extends PaginationParams {
  status?: 'draft' | 'pending' | 'approved' | 'processed' | 'paid';
  period?: string;
  startDate?: string;
  endDate?: string;
}

export interface PayrollStats {
  totalPayrolls: number;
  totalAmount: number;
  pendingAmount: number;
  paidAmount: number;
  averagePerPayroll: number;
}

// ============= Approval Types =============

export interface Approval {
  id: string;
  type: 'payroll' | 'expense' | 'leave' | 'promotion';
  referenceId: string;
  status: 'pending' | 'approved' | 'rejected';
  requestedBy: string;
  approverEmail: string;
  notes?: string;
  rejectionReason?: string;
  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
  amount?: number;
}

export interface ApprovalRequest {
  approvalId: string;
  action: 'approve' | 'reject';
  notes?: string;
  rejectionReason?: string;
}

export interface ApprovalStats {
  pendingCount: number;
  approvedCount: number;
  rejectedCount: number;
  averageApprovalTime: number; // in hours
}

// ============= Report Types =============

export interface Report {
  id: string;
  name: string;
  type: 'payroll' | 'tax' | 'compliance' | 'analytics';
  period: string;
  status: 'draft' | 'generating' | 'ready' | 'archived';
  format: 'pdf' | 'excel' | 'csv';
  fileSize?: number;
  downloadUrl?: string;
  createdBy: string;
  createdAt: string;
  expiresAt?: string;
}

export interface GenerateReportDto {
  name: string;
  type: 'payroll' | 'tax' | 'compliance' | 'analytics';
  period: string;
  format: 'pdf' | 'excel' | 'csv';
  filters?: Record<string, unknown>;
}

export interface ReportStats {
  totalReports: number;
  reportsThisMonth: number;
  averageGenerationTime: number; // in seconds
}

// ============= Dashboard Types =============

export interface DashboardStats {
  employees: EmployeeStats;
  payroll: PayrollStats;
  approvals: ApprovalStats;
  reports: ReportStats;
}

export interface DashboardData {
  stats: DashboardStats;
  recentPayrolls: Payroll[];
  pendingApprovals: Approval[];
  systemHealth: {
    status: 'healthy' | 'warning' | 'critical';
    lastCheck: string;
    uptime: number; // percentage
  };
}

// ============= Error Codes =============

export const ApiErrorCode = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  CONFLICT: 'CONFLICT',
  RATE_LIMITED: 'RATE_LIMITED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
} as const;

export type ApiErrorCodeType = typeof ApiErrorCode[keyof typeof ApiErrorCode];
