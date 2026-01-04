import { apiFetchWithCookies } from './api';

export type EmailSummary = {
  id: number;
  gmail_message_id: string;
  gmail_thread_id: string | null;
  internal_date_ts: string | null;
  subject: string | null;
  snippet: string | null;
  from_email: string | null;
  label_ids: string[] | null;
};

export async function getEmailsServer(cookieHeader: string): Promise<EmailSummary[]> {
  return apiFetchWithCookies<EmailSummary[]>('/api/emails?filter=inbox&limit=50&offset=0', cookieHeader);
}
