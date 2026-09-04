/**
 * Payroll Service
 * Handle payroll processing, approvals, and calculations
 */

import { apiClient } from './api';
import {
  Payroll,
  PayrollDetail,
  CreatePayrollDto,
  ProcessPayrollDto,
  ApprovePayrollDto,
  PayrollFilters,
  PayrollStats,
  PaginatedResponse,
} from '../types/api';

export const payrollService = {
  /**
   * Get all payrolls with optional filters
   */
  async getAll(filters?: PayrollFilters) {
    return apiClient.get<PaginatedResponse<Payroll>>('/payroll', {
      params: filters,
    });
  },

  /**
   * Get payroll by ID
   */
  async getById(id: string) {
    return apiClient.get<Payroll>(`/payroll/${id}`);
  },

  /**
   * Get payroll details (line items)
   */
  async getDetails(payrollId: string, filters?: any) {
    return apiClient.get<PaginatedResponse<PayrollDetail>>(
      `/payroll/${payrollId}/details`,
      { params: filters }
    );
  },

  /**
   * Create new payroll
   */
  async create(data: CreatePayrollDto) {
    return apiClient.post<Payroll>('/payroll', data);
  },

  /**
   * Process payroll (calculate deductions, taxes, etc.)
   */
  async process(data: ProcessPayrollDto) {
    return apiClient.post<Payroll>('/payroll/process', data);
  },

  /**
   * Approve payroll (manager approval)
   */
  async approve(data: ApprovePayrollDto) {
    return apiClient.post<Payroll>('/payroll/approve', data);
  },

  /**
   * Reject payroll
   */
  async reject(payrollId: string, reason: string) {
    return apiClient.post<Payroll>(`/payroll/${payrollId}/reject`, { reason });
  },

  /**
   * Finalize payroll for payment
   */
  async finalize(payrollId: string) {
    return apiClient.post<Payroll>(`/payroll/${payrollId}/finalize`);
  },

  /**
   * Mark payroll as paid
   */
  async markAsPaid(payrollId: string, paidDate: string) {
    return apiClient.post<Payroll>(`/payroll/${payrollId}/mark-paid`, { paidDate });
  },

  /**
   * Get payroll statistics
   */
  async getStats() {
    return apiClient.get<PayrollStats>('/payroll/stats');
  },

  /**
   * Get payroll history for employee
   */
  async getEmployeePayrollHistory(employeeId: string, filters?: any) {
    return apiClient.get<PayrollDetail[]>(
      `/payroll/employee/${employeeId}/history`,
      { params: filters }
    );
  },

  /**
   * Download payroll report
   */
  async downloadReport(payrollId: string, format: 'pdf' | 'excel' = 'pdf') {
    return apiClient.get(`/payroll/${payrollId}/report`, {
      params: { format },
      responseType: 'blob',
    });
  },

  /**
   * Validate payroll before processing
   */
  async validate(data: CreatePayrollDto) {
    return apiClient.post<{ valid: boolean; errors?: string[] }>(
      '/payroll/validate',
      data
    );
  },

  /**
   * Calculate net salary for employee
   */
  async calculateNetSalary(employeeId: string, period: string) {
    return apiClient.post<{ netSalary: number; breakdown: Record<string, number> }>(
      '/payroll/calculate-net',
      { employeeId, period }
    );
  },

  /**
   * Get pending payrolls awaiting approval
   */
  async getPendingApprovals(filters?: any) {
    return apiClient.get<PaginatedResponse<Payroll>>(
      '/payroll?status=pending',
      { params: filters }
    );
  },
};
