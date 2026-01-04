import { apiFetch } from './api';

export type CalendarCandidate = {
  id: number;
  email_id: number;
  payload: Record<string, unknown> | null;
  status: string | null;
  created_at: string;
  updated_at: string;
};

export type MeetingTimeSuggestion = {
  start: string;
  end: string;
  score?: number | null;
};

export type CalendarEventCreated = {
  id: number;
  calendar_candidate_id: number;
  event_id: string | null;
  payload: Record<string, unknown> | null;
  status: string | null;
  created_at: string;
  updated_at: string;
};

export type CalendarEventCreateRequest = {
  title?: string;
  start?: string;
  end?: string;
  timezone?: string;
  location?: string;
  attendees?: string[];
  description?: string;
};

export async function getCalendarCandidates(emailId: number): Promise<CalendarCandidate[]> {
  return apiFetch<CalendarCandidate[]>(`/api/emails/${emailId}/calendar/candidates`);
}

export async function proposeCalendarCandidates(emailId: number): Promise<CalendarCandidate[]> {
  return apiFetch<CalendarCandidate[]>(`/api/emails/${emailId}/calendar/propose`, {
    method: 'POST',
  });
}

export async function suggestMeetingTimes(
  candidateId: number,
  durationMin?: number,
): Promise<MeetingTimeSuggestion[]> {
  const body = durationMin ? JSON.stringify({ duration_min: durationMin }) : undefined;
  return apiFetch<{ candidate_id: number; suggestions: MeetingTimeSuggestion[] }>(
    `/api/calendar/candidates/${candidateId}/suggest_times`,
    {
      method: 'POST',
      body,
    },
  ).then((response) => response.suggestions);
}

export async function createCalendarEvent(
  candidateId: number,
  payload: CalendarEventCreateRequest,
): Promise<CalendarEventCreated> {
  return apiFetch<CalendarEventCreated>(`/api/calendar/candidates/${candidateId}/create_event`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function acceptCalendarInvite(candidateId: number): Promise<CalendarEventCreated> {
  return apiFetch<CalendarEventCreated>(`/api/calendar/candidates/${candidateId}/accept_invite`, {
    method: 'POST',
  });
}
