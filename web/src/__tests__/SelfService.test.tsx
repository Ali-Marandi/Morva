import '@testing-library/jest-dom/vitest';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import SelfService from '../pages/SelfService';
import { selfService } from '../services/self-service';

vi.mock('../services/self-service', () => ({
  selfService: {
    getProfile: vi.fn(),
    getPayslips: vi.fn(),
    getPayslip: vi.fn(),
    getPayslipPdf: vi.fn(),
    getOrders: vi.fn(),
  },
}));

const mockedSelfService = vi.mocked(selfService);

const renderPage = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <SelfService />
    </QueryClientProvider>,
  );
};

describe('SelfService', () => {
  it('shows payslip details only after the employee selects a payslip', async () => {
    mockedSelfService.getProfile.mockResolvedValue({
      data: {
        employee_no: 'E-100',
        first_name: 'علی',
        last_name: 'مرندی',
        employment_type: 'official',
        status: 'active',
        organization_unit_id: 'org-1',
        position_id: 'pos-1',
        hire_date: '2020-01-01',
      },
    } as never);
    mockedSelfService.getPayslips.mockResolvedValue({
      data: [{
        artifact_id: 'artifact-1',
        period: '۱۴۰۵-۰۶',
        currency_code: 'IRR',
        gross: '1000',
        deductions: '100',
        net: '900',
        status: 'frozen',
        personnel_snapshot_hash: 'snapshot-hash',
        rule_pack_version: '1405.1',
        output_hash: 'output-hash',
      }],
    } as never);
    mockedSelfService.getOrders.mockResolvedValue({ data: [] } as never);
    mockedSelfService.getPayslip.mockResolvedValue({
      data: {
        artifact_id: 'artifact-1',
        employee_no: 'E-100',
        period: '۱۴۰۵-۰۶',
        currency_code: 'IRR',
        gross: '1000',
        deductions: '100',
        net: '900',
        status: 'frozen',
        personnel_snapshot_id: 'snapshot-1',
        personnel_snapshot_hash: 'snapshot-hash',
        rule_pack_version: '1405.1',
        input_hash: 'input-hash',
        output_hash: 'output-hash',
        lines: [{
          sequence: 1,
          code: 'BASE',
          title: 'حقوق پایه',
          amount: '1000',
          kind: 'earning',
          taxable: true,
          pensionable: true,
          insurable: true,
          explanation: 'مبلغ پایه',
        }],
      },
    } as never);

    renderPage();
    await screen.findByText('۱۴۰۵-۰۶');
    expect(screen.queryByText('حقوق پایه')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'جزئیات' }));
    expect(await screen.findByText('حقوق پایه')).toBeInTheDocument();
    expect(screen.getByText('snapshot-hash')).toBeInTheDocument();
    expect(mockedSelfService.getPayslip).toHaveBeenCalledWith('artifact-1');
  });

  it('reports a PDF download failure without leaving the button busy', async () => {
    mockedSelfService.getProfile.mockResolvedValue({ data: { employee_no: 'E-100', first_name: 'علی', last_name: 'مرندی', employment_type: 'official', status: 'active', organization_unit_id: 'org-1', position_id: 'pos-1' } } as never);
    mockedSelfService.getPayslips.mockResolvedValue({ data: [{ artifact_id: 'artifact-2', period: '۱۴۰۵-۰۵', currency_code: 'IRR', gross: '100', deductions: '10', net: '90', status: 'approved', personnel_snapshot_hash: 'hash', rule_pack_version: '1405.1', output_hash: 'out' }] } as never);
    mockedSelfService.getOrders.mockResolvedValue({ data: [] } as never);
    mockedSelfService.getPayslipPdf.mockRejectedValue(new Error('download failed'));

    renderPage();
    await screen.findByText('۱۴۰۵-۰۵');
    const button = screen.getByRole('button', { name: 'PDF' });
    fireEvent.click(button);
    expect(await screen.findByText(/دریافت فایل PDF ناموفق بود/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: 'PDF' })).not.toBeDisabled());
  });
});
