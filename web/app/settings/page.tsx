'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { getPreferences, Preferences, updatePreferences } from '../../lib/preferences';

export default function SettingsPage() {
  const router = useRouter();
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [daysInput, setDaysInput] = useState('');
  const [vipSendersInput, setVipSendersInput] = useState('');
  const [vipDomainsInput, setVipDomainsInput] = useState('');
  const [vipKeywordsInput, setVipKeywordsInput] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getPreferences()
      .then((data) => {
        if (!active) return;
        setPreferences(data);
        setDaysInput(data.working_hours.days.join(', '));
        setVipSendersInput((data.vip_senders ?? []).join(', '));
        setVipDomainsInput((data.vip_domains ?? []).join(', '));
        setVipKeywordsInput((data.vip_keywords ?? []).join(', '));
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

  const applyUpdatedPreferences = (updated: Preferences) => {
    setPreferences(updated);
    setDaysInput(updated.working_hours.days.join(', '));
    setVipSendersInput((updated.vip_senders ?? []).join(', '));
    setVipDomainsInput((updated.vip_domains ?? []).join(', '));
    setVipKeywordsInput((updated.vip_keywords ?? []).join(', '));
  };

  const parseListInput = (value: string) =>
    value
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);

  const handleSaveDigest = async () => {
    if (!preferences) return;
    setStatus(null);
    try {
      const updated = await updatePreferences({
        digest_time_local: preferences.digest_time_local,
        vip_alerts_enabled: preferences.vip_alerts_enabled,
      });
      applyUpdatedPreferences(updated);
      setStatus('Digest and alert settings saved.');
    } catch {
      setStatus('Failed to save digest settings.');
    }
  };

  const handleSaveVipLists = async () => {
    if (!preferences) return;
    setStatus(null);
    try {
      const updated = await updatePreferences({
        vip_senders: parseListInput(vipSendersInput),
        vip_domains: parseListInput(vipDomainsInput),
        vip_keywords: parseListInput(vipKeywordsInput),
      });
      applyUpdatedPreferences(updated);
      setStatus('VIP lists saved.');
    } catch {
      setStatus('Failed to save VIP lists.');
    }
  };

  const handleSaveWorkingHours = async () => {
    if (!preferences) return;
    setStatus(null);
    const workingHours = {
      ...preferences.working_hours,
      days: parseListInput(daysInput).map((day) => day.toLowerCase()),
    };
    try {
      const updated = await updatePreferences({
        working_hours: workingHours,
      });
      applyUpdatedPreferences(updated);
      setStatus('Working hours saved.');
    } catch {
      setStatus('Failed to save working hours.');
    }
  };

  const handleSaveAutomation = async () => {
    if (!preferences) return;
    setStatus(null);
    try {
      const updated = await updatePreferences({
        meeting_default_duration_min: preferences.meeting_default_duration_min,
        automation_level: preferences.automation_level,
      });
      applyUpdatedPreferences(updated);
      setStatus('Automation settings saved.');
    } catch {
      setStatus('Failed to save automation settings.');
    }
  };

  if (!preferences) {
    return (
      <div className="page">
        <div className="card">
          <h3>Settings</h3>
          <p>Loading preferences...</p>
          {status ? <p>{status}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h2 className="page-title">Preferences</h2>
          <p className="page-subtitle">Tune your digest, alerts, and automation behavior.</p>
        </div>
      </header>
      {status ? <p className="status-text">{status}</p> : null}
      <div className="settings-grid">
        <section className="card">
          <h3>Digest & alerts</h3>
          <div className="form-row">
            <label htmlFor="digest_time_local">Digest time (HH:MM)</label>
            <p className="helper-text">Daily digest delivery time in your local timezone.</p>
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
            <p className="helper-text">Surface alerts when VIP senders or keywords appear.</p>
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
          <div className="card-actions">
            <button
              className="button"
              type="button"
              onClick={handleSaveDigest}
              title="Save digest and alert settings"
            >
              Save changes
            </button>
          </div>
        </section>
        <section className="card">
          <h3>VIP lists</h3>
          <div className="form-row">
            <label htmlFor="vip_senders">VIP senders (comma separated)</label>
            <p className="helper-text">Exact email addresses that should trigger alerts.</p>
            <input
              id="vip_senders"
              value={vipSendersInput}
              onChange={(event) => setVipSendersInput(event.target.value)}
            />
          </div>
          <div className="form-row">
            <label htmlFor="vip_domains">VIP domains (comma separated)</label>
            <p className="helper-text">Whole domains that should be treated as VIP.</p>
            <input
              id="vip_domains"
              value={vipDomainsInput}
              onChange={(event) => setVipDomainsInput(event.target.value)}
            />
          </div>
          <div className="form-row">
            <label htmlFor="vip_keywords">VIP keywords (comma separated)</label>
            <p className="helper-text">Alert on subject/body keywords that matter most.</p>
            <input
              id="vip_keywords"
              value={vipKeywordsInput}
              onChange={(event) => setVipKeywordsInput(event.target.value)}
            />
          </div>
          <div className="card-actions">
            <button
              className="button"
              type="button"
              onClick={handleSaveVipLists}
              title="Save VIP lists"
            >
              Save changes
            </button>
          </div>
        </section>
        <section className="card">
          <h3>Working hours</h3>
          <div className="form-row">
            <label htmlFor="working_days">Working days (comma separated)</label>
            <p className="helper-text">Used to suggest meeting times and avoid weekends.</p>
            <input
              id="working_days"
              value={daysInput}
              onChange={(event) => setDaysInput(event.target.value)}
            />
          </div>
          <div className="form-row">
            <label htmlFor="work_start">Earliest suggested meeting time</label>
            <p className="helper-text">Start of your preferred meeting window.</p>
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
            <label htmlFor="work_end">Latest suggested meeting time</label>
            <p className="helper-text">End of your preferred meeting window.</p>
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
            <div className="form-inline">
              <label htmlFor="lunch_enabled">Time block to avoid</label>
              <input
                id="lunch_enabled"
                type="checkbox"
                checked={preferences.working_hours.lunch_enabled}
                onChange={(event) =>
                  setPreferences({
                    ...preferences,
                    working_hours: {
                      ...preferences.working_hours,
                      lunch_enabled: event.target.checked,
                    },
                  })
                }
              />
            </div>
            <p className="helper-text">Optionally skip meetings during this block.</p>
            <div className="form-inline">
              <div className="form-field">
                <label htmlFor="lunch_start">Start</label>
                <input
                  id="lunch_start"
                  value={preferences.working_hours.lunch_start}
                  disabled={!preferences.working_hours.lunch_enabled}
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
              <div className="form-field">
                <label htmlFor="lunch_end">End</label>
                <input
                  id="lunch_end"
                  value={preferences.working_hours.lunch_end}
                  disabled={!preferences.working_hours.lunch_enabled}
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
            </div>
          </div>
          <div className="card-actions">
            <button
              className="button"
              type="button"
              onClick={handleSaveWorkingHours}
              title="Save working hours"
            >
              Save changes
            </button>
          </div>
        </section>
        <section className="card">
          <h3>Automation</h3>
          <div className="form-row">
            <label htmlFor="meeting_duration">Meeting duration (min)</label>
            <p className="helper-text">Default length for suggested meetings.</p>
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
            <p className="helper-text">Control how much the copilot acts without review.</p>
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
          <div className="card-actions">
            <button
              className="button"
              type="button"
              onClick={handleSaveAutomation}
              title="Save automation settings"
            >
              Save changes
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
