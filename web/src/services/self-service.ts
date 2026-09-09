import { apiClient } from './api';
import type { SelfCase, SelfPayslip, SelfProfile, SelfOrder, CreateCaseDto } from '../types/api';

export const selfService = {
  async getProfile() {
    return apiClient.get<SelfProfile>('/self/profile');
  },
  async getPayslips(period?: string) {
    return apiClient.get<SelfPayslip[]>('/self/payslips', { params: period ? { period } : undefined });
  },
  async getPayslip(id: string) {
    return apiClient.get<SelfPayslip>(`/self/payslips/${id}`);
  },
  async getPayslipPdf(id: string) {
    return apiClient.get(`/self/payslips/${id}/pdf`, { responseType: 'blob' });
  },
  async getOrders() {
    return apiClient.get<SelfOrder[]>('/self/orders');
  },
  async getCases(status?: string) {
    return apiClient.get<SelfCase[]>('/cases/self', { params: status ? { status } : undefined });
  },
  async getCase(id: string) {
    return apiClient.get<SelfCase>(`/cases/self/${id}`);
  },
  async createCase(data: CreateCaseDto) {
    return apiClient.post<SelfCase>('/cases/self', data);
  },
};
