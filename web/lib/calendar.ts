import { apiFetch } from './api';

export type CalendarCandidate = {
  id: number;
  email_id: number;
  payload: Record<string, unknown> | null;
  status: string | null;
  created_at: string;
  updated_at: string;
};

export async function getCalendarCandidates(emailId: number): Promise<CalendarCandidate[]> {
  return apiFetch<CalendarCandidate[]>(`/api/emails/${emailId}/calendar/candidates`);
}

export async function proposeCalendarCandidates(emailId: number): Promise<CalendarCandidate[]> {
  return apiFetch<CalendarCandidate[]>(`/api/emails/${emailId}/calendar/propose`, {
    method: 'POST',
  });
}
