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
  importance_label?: string | null;
  needs_response?: boolean | null;
  why_important?: string | null;
};

export async function getEmailsServer(cookieHeader: string): Promise<EmailSummary[]> {
  return apiFetchWithCookies<EmailSummary[]>(
    '/api/emails?filter=inbox&limit=50&offset=0',
    cookieHeader,
  );
}

export type AttachmentSummary = {
  id: number;
  filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  gmail_attachment_id: string | null;
  extraction_status: string | null;
};

export type EmailDetail = EmailSummary & {
  to_emails: string[] | null;
  clean_body_text: string | null;
  attachments: AttachmentSummary[];
  summary_bullets: string[];
  why_important?: string | null;
};

export async function getEmailDetailServer(
  cookieHeader: string,
  emailId: number,
): Promise<EmailDetail> {
  return apiFetchWithCookies<EmailDetail>(`/api/emails/${emailId}`, cookieHeader);
}
