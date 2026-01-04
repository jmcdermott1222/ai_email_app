'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { apiFetch } from '../../lib/api';

type WorkingHours = {
  days: string[];
  start_time: string;
  end_time: string;
  lunch_start: string;
  lunch_end: string;
};

type Preferences = {
  digest_time_local: string;
  vip_alerts_enabled: boolean;
  working_hours: WorkingHours;
  meeting_default_duration_min: number;
  automation_level: 'SUGGEST_ONLY' | 'AUTO_LABEL' | 'AUTO_ARCHIVE' | 'AUTO_TRASH';
};

export default function SettingsPage() {
  const router = useRouter();
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [daysInput, setDaysInput] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<Preferences>('/api/preferences')
      .then((data) => {
        if (!active) return;
        setPreferences(data);
        setDaysInput(data.working_hours.days.join(', '));
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : '';
        if (message.includes('401')) {
          router.push('/login');
          return;
        }
        setStatus('Failed to load preferences.');
      });

    return () => {
      active = false;
    };
  }, [router]);

  const handleSave = async () => {
    if (!preferences) return;
    setStatus(null);
    const payload = {
      ...preferences,
      working_hours: {
        ...preferences.working_hours,
        days: daysInput
          .split(',')
          .map((day) => day.trim().toLowerCase())
          .filter(Boolean),
      },
    };

    try {
      const updated = await apiFetch<Preferences>('/api/preferences', {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      setPreferences(updated);
      setDaysInput(updated.working_hours.days.join(', '));
      setStatus('Preferences saved.');
    } catch {
      setStatus('Failed to save preferences.');
    }
  };

  if (!preferences) {
    return (
      <div className="card">
        <h3>Settings</h3>
        <p>Loading preferences...</p>
        {status ? <p>{status}</p> : null}
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Settings</h3>
      <div className="form-row">
        <label htmlFor="digest_time_local">Digest time (HH:MM)</label>
        <input
          id="digest_time_local"
          value={preferences.digest_time_local}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              digest_time_local: event.target.value,
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="vip_alerts_enabled">VIP alerts enabled</label>
        <input
          id="vip_alerts_enabled"
          type="checkbox"
          checked={preferences.vip_alerts_enabled}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              vip_alerts_enabled: event.target.checked,
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="working_days">Working days (comma separated)</label>
        <input
          id="working_days"
          value={daysInput}
          onChange={(event) => setDaysInput(event.target.value)}
        />
      </div>
      <div className="form-row">
        <label htmlFor="work_start">Work start</label>
        <input
          id="work_start"
          value={preferences.working_hours.start_time}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              working_hours: {
                ...preferences.working_hours,
                start_time: event.target.value,
              },
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="work_end">Work end</label>
        <input
          id="work_end"
          value={preferences.working_hours.end_time}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              working_hours: {
                ...preferences.working_hours,
                end_time: event.target.value,
              },
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="lunch_start">Lunch start</label>
        <input
          id="lunch_start"
          value={preferences.working_hours.lunch_start}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              working_hours: {
                ...preferences.working_hours,
                lunch_start: event.target.value,
              },
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="lunch_end">Lunch end</label>
        <input
          id="lunch_end"
          value={preferences.working_hours.lunch_end}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              working_hours: {
                ...preferences.working_hours,
                lunch_end: event.target.value,
              },
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="meeting_duration">Meeting duration (min)</label>
        <input
          id="meeting_duration"
          type="number"
          value={preferences.meeting_default_duration_min}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              meeting_default_duration_min: Number(event.target.value),
            })
          }
        />
      </div>
      <div className="form-row">
        <label htmlFor="automation_level">Automation level</label>
        <select
          id="automation_level"
          value={preferences.automation_level}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              automation_level: event.target.value as Preferences['automation_level'],
            })
          }
        >
          <option value="SUGGEST_ONLY">Suggest only</option>
          <option value="AUTO_LABEL">Auto label</option>
          <option value="AUTO_ARCHIVE">Auto archive</option>
          <option value="AUTO_TRASH">Auto trash</option>
        </select>
      </div>
      <button className="button" type="button" onClick={handleSave}>
        Save preferences
      </button>
      {status ? <p>{status}</p> : null}
    </div>
  );
}
