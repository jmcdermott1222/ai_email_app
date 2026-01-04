import { apiFetch } from './api';

export type WorkingHours = {
  days: string[];
  start_time: string;
  end_time: string;
  lunch_enabled: boolean;
  lunch_start: string;
  lunch_end: string;
};

export type Preferences = {
  digest_time_local: string;
  vip_alerts_enabled: boolean;
  working_hours: WorkingHours;
  meeting_default_duration_min: number;
  vip_senders: string[];
  vip_domains: string[];
  vip_keywords: string[];
  automation_level: 'SUGGEST_ONLY' | 'AUTO_LABEL' | 'AUTO_ARCHIVE' | 'AUTO_TRASH';
};

export type PreferencesUpdate = Partial<Preferences> & {
  working_hours?: Partial<WorkingHours> | null;
};

export async function getPreferences(): Promise<Preferences> {
  return apiFetch<Preferences>('/api/preferences');
}

export async function updatePreferences(payload: PreferencesUpdate): Promise<Preferences> {
  return apiFetch<Preferences>('/api/preferences', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
