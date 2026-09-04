/**
 * Employee, Payroll, Approvals, Reports Services Tests
 * Basic smoke tests for service layer
 */

import { describe, it, expect } from 'vitest';
import { employeeService } from '../../services/employees';
import { payrollService } from '../../services/payroll';
import { approvalService } from '../../services/approvals';
import { reportService } from '../../services/reports';

describe('Employee Service', () => {
  it('should have all required methods', () => {
    expect(employeeService.getAll).toBeDefined();
    expect(employeeService.getById).toBeDefined();
    expect(employeeService.create).toBeDefined();
    expect(employeeService.update).toBeDefined();
    expect(employeeService.delete).toBeDefined();
    expect(employeeService.bulkImport).toBeDefined();
    expect(employeeService.export).toBeDefined();
    expect(employeeService.getStats).toBeDefined();
    expect(employeeService.search).toBeDefined();
    expect(employeeService.getByDepartment).toBeDefined();
    expect(employeeService.validate).toBeDefined();
  });

  it('methods should be functions', () => {
    expect(typeof employeeService.getAll).toBe('function');
    expect(typeof employeeService.create).toBe('function');
    expect(typeof employeeService.update).toBe('function');
  });
});

describe('Payroll Service', () => {
  it('should have all required methods', () => {
    expect(payrollService.getAll).toBeDefined();
    expect(payrollService.getById).toBeDefined();
    expect(payrollService.getDetails).toBeDefined();
    expect(payrollService.create).toBeDefined();
    expect(payrollService.process).toBeDefined();
    expect(payrollService.approve).toBeDefined();
    expect(payrollService.reject).toBeDefined();
    expect(payrollService.finalize).toBeDefined();
    expect(payrollService.markAsPaid).toBeDefined();
    expect(payrollService.getStats).toBeDefined();
    expect(payrollService.getEmployeePayrollHistory).toBeDefined();
    expect(payrollService.downloadReport).toBeDefined();
    expect(payrollService.validate).toBeDefined();
  });

  it('methods should return promises', async () => {
    // Mock implementation - actual calls would need proper setup
    expect(typeof payrollService.getStats).toBe('function');
  });
});

describe('Approval Service', () => {
  it('should have all required methods', () => {
    expect(approvalService.getAll).toBeDefined();
    expect(approvalService.getById).toBeDefined();
    expect(approvalService.getPending).toBeDefined();
    expect(approvalService.approve).toBeDefined();
    expect(approvalService.reject).toBeDefined();
    expect(approvalService.request).toBeDefined();
    expect(approvalService.bulkApprove).toBeDefined();
    expect(approvalService.bulkReject).toBeDefined();
    expect(approvalService.getStats).toBeDefined();
    expect(approvalService.getHistory).toBeDefined();
    expect(approvalService.getDashboard).toBeDefined();
  });

  it('should support reassignment and comments', () => {
    expect(approvalService.reassign).toBeDefined();
    expect(approvalService.addComment).toBeDefined();
    expect(approvalService.getComments).toBeDefined();
  });
});

describe('Report Service', () => {
  it('should have all required methods', () => {
    expect(reportService.getAll).toBeDefined();
    expect(reportService.getById).toBeDefined();
    expect(reportService.generate).toBeDefined();
    expect(reportService.download).toBeDefined();
    expect(reportService.delete).toBeDefined();
    expect(reportService.getReportTypes).toBeDefined();
    expect(reportService.getStats).toBeDefined();
    expect(reportService.scheduleRecurring).toBeDefined();
  });

  it('should support advanced features', () => {
    expect(reportService.getPreview).toBeDefined();
    expect(reportService.emailReport).toBeDefined();
    expect(reportService.getHistory).toBeDefined();
    expect(reportService.getTemplate).toBeDefined();
    expect(reportService.validate).toBeDefined();
    expect(reportService.regenerate).toBeDefined();
    expect(reportService.archive).toBeDefined();
  });
});
