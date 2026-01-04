import { apiFetch, apiFetchWithCookies } from './api';

export type Alert = {
  id: number;
  user_id: number;
  email_id: number;
  reason: string | null;
  read_at: string | null;
  created_at: string;
  updated_at: string;
  email_subject: string | null;
  email_from: string | null;
  email_snippet: string | null;
  email_internal_date_ts: string | null;
};

export async function getAlertsServer(cookieHeader: string): Promise<Alert[]> {
  return apiFetchWithCookies<Alert[]>('/api/alerts', cookieHeader);
}

export async function markAlertRead(alertId: number): Promise<Alert> {
  return apiFetch<Alert>(`/api/alerts/${alertId}/mark_read`, { method: 'POST' });
}
