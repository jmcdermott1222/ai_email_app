import { apiFetch } from './api';

export type Draft = {
  id: number;
  email_id: number;
  subject: string | null;
  body: string | null;
  status: string | null;
  gmail_draft_id: string | null;
  created_at: string;
  updated_at: string;
};

export async function getDrafts(emailId?: number): Promise<Draft[]> {
  const params = emailId ? `?email_id=${emailId}` : '';
  return apiFetch<Draft[]>(`/api/drafts${params}`);
}
