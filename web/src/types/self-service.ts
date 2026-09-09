export interface SelfProfile {
  employee_no: string;
  first_name: string;
  last_name: string;
  employment_type: string;
  status: string;
  organization_unit_id: string;
  position_id: string;
  hire_date?: string | null;
}

export interface SelfPayslipLine {
  sequence: number;
  code: string;
  title: string;
  amount: string;
  kind: string;
  taxable: boolean;
  pensionable: boolean;
  insurable: boolean;
  rule_code?: string | null;
  legal_source_id?: string | null;
  explanation?: string | null;
}

export interface SelfPayslip {
  artifact_id: string;
  employee_no?: string;
  period: string;
  currency_code: string;
  gross: string;
  deductions: string;
  net: string;
  status: string;
  personnel_snapshot_id?: string;
  personnel_snapshot_hash: string;
  rule_pack_version: string;
  rule_pack_hash?: string;
  input_hash?: string;
  output_hash: string;
  lines?: SelfPayslipLine[];
}

export interface SelfOrder {
  order_no: string;
  order_type: string;
  issue_date: string;
  effective_date: string;
  legal_reference?: string | null;
  reason?: string | null;
}

export interface SelfCase {
  id: string;
  employee_no: string;
  category: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  resolution?: string | null;
  submitted_by: string;
  submitted_at: string;
  updated_at: string;
  resolved_by?: string | null;
  resolved_at?: string | null;
}

export interface CreateCaseDto {
  category: 'payroll' | 'personnel_order' | 'attendance' | 'deduction' | 'other';
  title: string;
  description: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
}
