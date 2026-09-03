/**
 * Approval Service
 * Handle approval workflows (payroll, expenses, leaves, etc.)
 */

import { apiClient } from './api';
import {
  Approval,
  ApprovalRequest,
  ApprovalStats,
  PaginatedResponse,
} from '../types/api';

export const approvalService = {
  /**
   * Get all approvals with optional filters
   */
  async getAll(filters?: any) {
    return apiClient.get<PaginatedResponse<Approval>>('/approvals', {
      params: filters,
    });
  },

  /**
   * Get approval by ID
   */
  async getById(id: string) {
    return apiClient.get<Approval>(`/approvals/${id}`);
  },

  /**
   * Get pending approvals for current user
   */
  async getPending(filters?: any) {
    return apiClient.get<PaginatedResponse<Approval>>(
      '/approvals?status=pending',
      { params: filters }
    );
  },

  /**
   * Approve a request
   */
  async approve(approvalId: string, notes?: string) {
    const request: ApprovalRequest = {
      approvalId,
      action: 'approve',
      notes,
    };
    return apiClient.put<Approval>(
      `/approvals/${approvalId}/approve`,
      request
    );
  },

  /**
   * Reject a request
   */
  async reject(approvalId: string, rejectionReason: string, notes?: string) {
    const request: ApprovalRequest = {
      approvalId,
      action: 'reject',
      notes,
      rejectionReason,
    };
    return apiClient.put<Approval>(
      `/approvals/${approvalId}/reject`,
      request
    );
  },

  /**
   * Request approval (submit for approval)
   */
  async request(type: string, referenceId: string, notes?: string) {
    return apiClient.post<Approval>('/approvals/request', {
      type,
      referenceId,
      notes,
    });
  },

  /**
   * Bulk approve multiple requests
   */
  async bulkApprove(approvalIds: string[], notes?: string) {
    return apiClient.post<{ approved: number; failed: number }>(
      '/approvals/bulk-approve',
      { approvalIds, notes }
    );
  },

  /**
   * Bulk reject multiple requests
   */
  async bulkReject(approvalIds: string[], reason: string) {
    return apiClient.post<{ rejected: number; failed: number }>(
      '/approvals/bulk-reject',
      { approvalIds, reason }
    );
  },

  /**
   * Get approval statistics
   */
  async getStats() {
    return apiClient.get<ApprovalStats>('/approvals/stats');
  },

  /**
   * Get approval history for reference
   */
  async getHistory(type: string, referenceId: string) {
    return apiClient.get<Approval[]>('/approvals/history', {
      params: { type, referenceId },
    });
  },

  /**
   * Get approval dashboard (pending by category)
   */
  async getDashboard() {
    return apiClient.get<Record<string, number>>('/approvals/dashboard');
  },

  /**
   * Assign approval to another user
   */
  async reassign(approvalId: string, newApproverEmail: string) {
    return apiClient.post<Approval>(`/approvals/${approvalId}/reassign`, {
      newApproverEmail,
    });
  },

  /**
   * Add comment to approval
   */
  async addComment(approvalId: string, comment: string) {
    return apiClient.post(`/approvals/${approvalId}/comments`, { comment });
  },

  /**
   * Get approval comments
   */
  async getComments(approvalId: string) {
    return apiClient.get<any[]>(`/approvals/${approvalId}/comments`);
  },
};
