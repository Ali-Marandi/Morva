/**
 * Reports Service
 * Handle report generation, download, and distribution
 */

import { apiClient } from './api';
import {
  Report,
  GenerateReportDto,
  ReportStats,
  PaginatedResponse,
} from '../types/api';

export const reportService = {
  /**
   * Get all reports with optional filters
   */
  async getAll(filters?: any) {
    return apiClient.get<PaginatedResponse<Report>>('/reports', {
      params: filters,
    });
  },

  /**
   * Get report by ID
   */
  async getById(id: string) {
    return apiClient.get<Report>(`/reports/${id}`);
  },

  /**
   * Generate new report
   */
  async generate(data: GenerateReportDto) {
    return apiClient.post<Report>('/reports/generate', data);
  },

  /**
   * Download report file
   */
  async download(reportId: string) {
    return apiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
  },

  /**
   * Delete report
   */
  async delete(reportId: string) {
    return apiClient.delete(`/reports/${reportId}`);
  },

  /**
   * Get available report types
   */
  async getReportTypes() {
    return apiClient.get<string[]>('/reports/types');
  },

  /**
   * Get report statistics
   */
  async getStats() {
    return apiClient.get<ReportStats>('/reports/stats');
  },

  /**
   * Schedule recurring report
   */
  async scheduleRecurring(data: {
    name: string;
    type: string;
    period: string;
    format: string;
    frequency: 'daily' | 'weekly' | 'monthly';
    recipients: string[];
  }) {
    return apiClient.post('/reports/schedule', data);
  },

  /**
   * Get scheduled reports
   */
  async getScheduled() {
    return apiClient.get<any[]>('/reports/scheduled');
  },

  /**
   * Cancel scheduled report
   */
  async cancelScheduled(scheduleId: string) {
    return apiClient.delete(`/reports/scheduled/${scheduleId}`);
  },

  /**
   * Get report preview
   */
  async getPreview(data: GenerateReportDto) {
    return apiClient.post<{ preview: string }>('/reports/preview', data);
  },

  /**
   * Email report to recipients
   */
  async emailReport(reportId: string, recipients: string[], message?: string) {
    return apiClient.post(`/reports/${reportId}/email`, {
      recipients,
      message,
    });
  },

  /**
   * Get report history
   */
  async getHistory(limit = 20) {
    return apiClient.get<Report[]>('/reports/history', {
      params: { limit },
    });
  },

  /**
   * Export report template
   */
  async getTemplate(type: string) {
    return apiClient.get('/reports/template', {
      params: { type },
      responseType: 'blob',
    });
  },

  /**
   * Validate report generation
   */
  async validate(data: GenerateReportDto) {
    return apiClient.post<{ valid: boolean; errors?: string[] }>(
      '/reports/validate',
      data
    );
  },

  /**
   * Get reports by type
   */
  async getByType(type: string, filters?: any) {
    return apiClient.get<PaginatedResponse<Report>>('/reports', {
      params: { type, ...filters },
    });
  },

  /**
   * Regenerate existing report
   */
  async regenerate(reportId: string) {
    return apiClient.post<Report>(`/reports/${reportId}/regenerate`);
  },

  /**
   * Archive report
   */
  async archive(reportId: string) {
    return apiClient.post(`/reports/${reportId}/archive`);
  },
};
