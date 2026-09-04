/**
 * Employee Service
 * Handle employee data operations (CRUD)
 */

import { apiClient } from './api';
import {
  Employee,
  CreateEmployeeDto,
  UpdateEmployeeDto,
  EmployeeFilters,
  EmployeeStats,
  PaginatedResponse,
} from '../types/api';

export const employeeService = {
  /**
   * Get all employees with optional filters
   */
  async getAll(filters?: EmployeeFilters) {
    return apiClient.get<PaginatedResponse<Employee>>('/employees', {
      params: filters,
    });
  },

  /**
   * Get employee by ID
   */
  async getById(id: string) {
    return apiClient.get<Employee>(`/employees/${id}`);
  },

  /**
   * Create new employee
   */
  async create(data: CreateEmployeeDto) {
    return apiClient.post<Employee>('/employees', data);
  },

  /**
   * Update employee
   */
  async update(id: string, data: UpdateEmployeeDto) {
    return apiClient.put<Employee>(`/employees/${id}`, data);
  },

  /**
   * Delete employee
   */
  async delete(id: string) {
    return apiClient.delete(`/employees/${id}`);
  },

  /**
   * Bulk import employees
   */
  async bulkImport(employees: CreateEmployeeDto[]) {
    return apiClient.post<{ imported: number; errors: any[] }>(
      '/employees/bulk-import',
      { employees }
    );
  },

  /**
   * Export employees to CSV/Excel
   */
  async export(format: 'csv' | 'excel', filters?: EmployeeFilters) {
    return apiClient.get('/employees/export', {
      params: { format, ...filters },
      responseType: 'blob',
    });
  },

  /**
   * Get employee statistics
   */
  async getStats() {
    return apiClient.get<EmployeeStats>('/employees/stats');
  },

  /**
   * Search employees
   */
  async search(query: string, limit = 10) {
    return apiClient.get<Employee[]>('/employees/search', {
      params: { q: query, limit },
    });
  },

  /**
   * Get employees by department
   */
  async getByDepartment(department: string, filters?: Omit<EmployeeFilters, 'department'>) {
    return apiClient.get<PaginatedResponse<Employee>>('/employees', {
      params: { department, ...filters },
    });
  },

  /**
   * Validate employee data
   */
  async validate(data: CreateEmployeeDto | UpdateEmployeeDto) {
    return apiClient.post<{ valid: boolean; errors?: Record<string, string> }>(
      '/employees/validate',
      data
    );
  },
};
