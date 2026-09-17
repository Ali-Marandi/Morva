import { apiClient } from './api';

export type PaymentExceptionStatus = 'open' | 'resolved' | 'blocked';
export type PaymentExceptionType = 'return' | 'reject' | 'partial_settlement' | 'reversal' | 'unresolved_mismatch';

export interface PaymentException {
  exception_id: string;
  payment_item_id: string;
  exception_type: PaymentExceptionType;
  reason: string;
  status: PaymentExceptionStatus;
  opened_at: string;
  resolved_at?: string | null;
  resolution_actor?: string | null;
  resolution_reason?: string | null;
  evidence_ref?: string | null;
  resolution_fingerprint?: string | null;
}

export interface PaymentExceptionEvent {
  exception_id: string;
  status: PaymentExceptionStatus;
  actor: string;
  reason: string;
  evidence_ref: string;
  occurred_at: string;
  idempotency_key: string;
  fingerprint: string;
}

export const paymentExceptionService = {
  async list(paymentItemId?: string, includeResolved = false): Promise<PaymentException[]> {
    const params = new URLSearchParams();
    if (paymentItemId?.trim()) params.set('payment_item_id', paymentItemId.trim());
    if (includeResolved) params.set('include_resolved', 'true');
    const query = params.toString();
    const response = await apiClient.get<PaymentException[]>(`/api/v1/payment-exceptions${query ? `?${query}` : ''}`);
    return response.data || [];
  },
  async events(exceptionId: string): Promise<PaymentExceptionEvent[]> {
    const response = await apiClient.get<PaymentExceptionEvent[]>(`/api/v1/payment-exceptions/${encodeURIComponent(exceptionId)}/events`);
    return response.data || [];
  },
  async resolve(exceptionId: string, reason: string, evidenceRef: string): Promise<PaymentExceptionEvent> {
    const response = await apiClient.post<PaymentExceptionEvent>(
      `/api/v1/payment-exceptions/${encodeURIComponent(exceptionId)}/resolve`,
      { reason, evidence_ref: evidenceRef },
      { headers: { 'Idempotency-Key': crypto.randomUUID() } },
    );
    if (!response.data) throw new Error('پاسخ نامعتبر از سرویس استثنای پرداخت دریافت شد.');
    return response.data;
  },
};
