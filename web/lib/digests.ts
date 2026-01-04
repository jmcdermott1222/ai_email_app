import { apiFetch, apiFetchWithCookies } from './api';

export type DigestEmail = {
  id: number;
  subject: string | null;
  from_email: string | null;
  snippet: string | null;
  internal_date_ts: string | null;
  importance_label: string | null;
  needs_response: boolean | null;
  why_important: string | null;
  summary_bullets: string[];
};

export type DigestContent = {
  generated_at: string;
  since_ts: string;
  triaged_count: number;
  triage_cap?: number;
  triage_cap_hit?: boolean;
  vip_count?: number;
  vip_senders?: string[];
  counts: Record<string, number>;
  sections: {
    needs_reply: DigestEmail[];
    important_fyi: DigestEmail[];
    newsletters: DigestEmail[];
    everything_else: DigestEmail[];
  };
};

export type Digest = {
  id: number;
  user_id: number;
  digest_date: string;
  content_json: DigestContent | null;
  created_at: string;
  updated_at: string;
};

export async function getLatestDigestServer(cookieHeader: string): Promise<Digest | null> {
  try {
    return await apiFetchWithCookies<Digest>('/api/digests/latest', cookieHeader);
  } catch (error) {
    const message = error instanceof Error ? error.message : '';
    if (message.includes('404')) {
      return null;
    }
    throw error;
  }
}

export async function runDigestNow(): Promise<Digest> {
  return apiFetch<Digest>('/api/digests/run_now', { method: 'POST' });
}
