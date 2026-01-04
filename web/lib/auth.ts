import { cookies } from 'next/headers';

import { apiFetch, apiFetchWithCookies } from './api';

export type GoogleIntegrationStatus = {
  connected: boolean;
  token_status: string | null;
  needs_reauth: boolean;
  last_error: string | null;
};

export async function getGoogleIntegrationStatus(): Promise<GoogleIntegrationStatus> {
  return apiFetch<GoogleIntegrationStatus>('/api/integrations/google/status');
}

export async function getGoogleIntegrationStatusServer(): Promise<GoogleIntegrationStatus> {
  const cookieStore = cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join('; ');

  return apiFetchWithCookies<GoogleIntegrationStatus>(
    '/api/integrations/google/status',
    cookieHeader,
  );
}
