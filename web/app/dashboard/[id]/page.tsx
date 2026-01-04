'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { apiFetch } from '../../../lib/api';
import {
  CalendarCandidate,
  CalendarEventCreateRequest,
  CalendarEventCreated,
  getCalendarCandidates,
  proposeCalendarCandidates,
  suggestMeetingTimes,
  createCalendarEvent,
  MeetingTimeSuggestion,
} from '../../../lib/calendar';
import { Draft, getDrafts } from '../../../lib/drafts';
import { AttachmentSummary, EmailDetail } from '../../../lib/emails';
import FeedbackControls from '../../components/feedback-controls';

const pad = (value: number) => String(value).padStart(2, '0');

const toLocalInputValue = (isoString: string) => {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const toIsoString = (localValue: string) => {
  if (!localValue) return '';
  const date = new Date(localValue);
  if (Number.isNaN(date.getTime())) return '';
  return date.toISOString();
};

const parseAttendees = (value: string) =>
  value
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);

const getDefaultTimeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

const buildDefaultDescription = (email: EmailDetail) => {
  const link = email.gmail_message_id
    ? `https://mail.google.com/mail/u/0/#inbox/${email.gmail_message_id}`
    : '';
  return [
    'Created from AI Email Copilot.',
    email.subject ? `Email subject: ${email.subject}` : '',
    link ? `Email link: ${link}` : '',
  ]
    .filter(Boolean)
    .join('\n');
};

const readSuggestedTimes = (payload: Record<string, unknown> | null) => {
  if (!payload) return [];
  const items = payload.suggested_times;
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const entry = item as { start?: unknown; end?: unknown; score?: unknown };
      if (typeof entry.start !== 'string' || typeof entry.end !== 'string') {
        return null;
      }
      return {
        start: entry.start,
        end: entry.end,
        score: typeof entry.score === 'number' ? entry.score : undefined,
      };
    })
    .filter((item): item is MeetingTimeSuggestion => Boolean(item));
};

export default function EmailDetailPage() {
  const params = useParams();
  const router = useRouter();
  const emailId = Number(params.id);
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [snoozeUntil, setSnoozeUntil] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [draftStatus, setDraftStatus] = useState<string | null>(null);
  const [calendarCandidates, setCalendarCandidates] = useState<CalendarCandidate[]>([]);
  const [calendarStatus, setCalendarStatus] = useState<string | null>(null);
  const [activeCandidate, setActiveCandidate] = useState<CalendarCandidate | null>(null);
  const [meetingSuggestions, setMeetingSuggestions] = useState<MeetingTimeSuggestion[]>([]);
  const [meetingStatus, setMeetingStatus] = useState<string | null>(null);
  const [eventStatus, setEventStatus] = useState<string | null>(null);
  const [eventLink, setEventLink] = useState<string | null>(null);
  const [eventForm, setEventForm] = useState({
    title: '',
    start: '',
    end: '',
    timezone: '',
    location: '',
    attendees: '',
    description: '',
  });

  useEffect(() => {
    if (!emailId) return;
    apiFetch<EmailDetail>(`/api/emails/${emailId}`)
      .then((data) => {
        setEmail(data);
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : '';
        if (message.includes('401')) {
          router.push('/login');
          return;
        }
        setStatus('Failed to load email.');
      });
  }, [emailId, router]);

  useEffect(() => {
    if (!emailId) return;
    getDrafts(emailId)
      .then((drafts) => {
        const latest = drafts[0] ?? null;
        setDraft(latest);
        setDraftSubject(latest?.subject ?? '');
        setDraftBody(latest?.body ?? '');
      })
      .catch(() => {
        setDraftStatus('Failed to load drafts.');
      });
  }, [emailId]);

  useEffect(() => {
    if (!emailId) return;
    getCalendarCandidates(emailId)
      .then((candidates) => {
        setCalendarCandidates(candidates);
      })
      .catch(() => {
        setCalendarStatus('Failed to load calendar candidates.');
      });
  }, [emailId]);

  useEffect(() => {
    if (!activeCandidate) return;
    const existing = readSuggestedTimes(activeCandidate.payload);
    setMeetingSuggestions(existing);
    setMeetingStatus('Loading suggestions...');
    setEventLink(null);
    suggestMeetingTimes(activeCandidate.id)
      .then((suggestions) => {
        setMeetingSuggestions(suggestions);
        setMeetingStatus(null);
      })
      .catch(() => {
        setMeetingStatus('Failed to load suggestions.');
      });
  }, [activeCandidate]);

  const handleProcessAttachments = async () => {
    if (!emailId) return;
    setStatus(null);
    try {
      await apiFetch(`/api/emails/${emailId}/attachments/process`, { method: 'POST' });
      const refreshed = await apiFetch<EmailDetail>(`/api/emails/${emailId}`);
      setEmail(refreshed);
      setStatus('Attachment extraction complete.');
    } catch {
      setStatus('Attachment extraction failed.');
    }
  };

  const handleAction = async (action: string) => {
    if (!emailId) return;
    setStatus(null);
    try {
      await apiFetch(`/api/emails/${emailId}/actions`, {
        method: 'POST',
        body: JSON.stringify({ actions: [action] }),
      });
      setStatus('Action applied.');
    } catch {
      setStatus('Action failed.');
    }
  };

  const handleSnooze = async () => {
    if (!snoozeUntil) {
      setStatus('Pick a snooze time.');
      return;
    }
    const date = new Date(snoozeUntil);
    if (Number.isNaN(date.getTime())) {
      setStatus('Invalid snooze time.');
      return;
    }
    await handleAction(`SNOOZE_UNTIL:${date.toISOString()}`);
  };

  const handleRunTriage = async () => {
    if (!emailId) return;
    setStatus(null);
    try {
      await apiFetch(`/api/emails/${emailId}/triage`, { method: 'POST' });
      const refreshed = await apiFetch<EmailDetail>(`/api/emails/${emailId}`);
      setEmail(refreshed);
      setStatus('Triage complete.');
    } catch {
      setStatus('Triage failed.');
    }
  };

  const handleRunAutomation = async () => {
    if (!emailId) return;
    setStatus(null);
    try {
      await apiFetch(`/api/automation/run_for_email/${emailId}`, { method: 'POST' });
      setStatus('Automation complete.');
    } catch {
      setStatus('Automation failed.');
    }
  };

  const handleProposeDraft = async () => {
    if (!emailId) return;
    setDraftStatus(null);
    try {
      const proposed = await apiFetch<Draft>(`/api/emails/${emailId}/draft/propose`, {
        method: 'POST',
      });
      setDraft(proposed);
      setDraftSubject(proposed.subject ?? '');
      setDraftBody(proposed.body ?? '');
      setDraftStatus('Draft proposed.');
    } catch {
      setDraftStatus('Draft proposal failed.');
    }
  };

  const handleCreateGmailDraft = async () => {
    if (!draft) return;
    setDraftStatus(null);
    try {
      const created = await apiFetch<Draft>(`/api/drafts/${draft.id}/create_in_gmail`, {
        method: 'POST',
        body: JSON.stringify({ subject: draftSubject, body: draftBody }),
      });
      setDraft(created);
      setDraftStatus('Draft created in Gmail.');
    } catch {
      setDraftStatus('Failed to create Gmail draft.');
    }
  };

  const handleProposeCalendar = async () => {
    if (!emailId) return;
    setCalendarStatus(null);
    try {
      const candidates = await proposeCalendarCandidates(emailId);
      setCalendarCandidates(candidates);
      setCalendarStatus('Calendar candidates generated.');
    } catch {
      setCalendarStatus('Failed to extract calendar candidates.');
    }
  };

  const handleCreateEvent = (candidate: CalendarCandidate) => {
    setActiveCandidate(candidate);
    setEventStatus(null);
    setMeetingStatus(null);
    const payload = candidate.payload ?? {};
    const title = typeof payload.title === 'string' ? payload.title : (email?.subject ?? '');
    const start = typeof payload.start === 'string' ? toLocalInputValue(payload.start) : '';
    const end = typeof payload.end === 'string' ? toLocalInputValue(payload.end) : '';
    const attendees = Array.isArray(payload.attendees) ? payload.attendees.join(', ') : '';
    const location = typeof payload.location === 'string' ? payload.location : '';
    const timezone = getDefaultTimeZone();
    const description = email ? buildDefaultDescription(email) : '';
    setEventForm({
      title: title ?? '',
      start,
      end,
      timezone,
      location,
      attendees,
      description,
    });
  };

  const handleSelectSuggestion = (suggestion: MeetingTimeSuggestion) => {
    setEventForm((prev) => ({
      ...prev,
      start: toLocalInputValue(suggestion.start),
      end: toLocalInputValue(suggestion.end),
    }));
  };

  const handleSubmitEvent = async () => {
    if (!activeCandidate) return;
    setEventStatus(null);
    if (!eventForm.start || !eventForm.end) {
      setEventStatus('Start and end are required.');
      return;
    }
    const request: CalendarEventCreateRequest = {
      title: eventForm.title || undefined,
      start: toIsoString(eventForm.start) || undefined,
      end: toIsoString(eventForm.end) || undefined,
      timezone: eventForm.timezone || undefined,
      location: eventForm.location || undefined,
      attendees: parseAttendees(eventForm.attendees),
      description: eventForm.description || undefined,
    };
    try {
      const created: CalendarEventCreated = await createCalendarEvent(activeCandidate.id, request);
      const link =
        created.payload && typeof created.payload.htmlLink === 'string'
          ? created.payload.htmlLink
          : null;
      setEventLink(link);
      setEventStatus('Event created.');
    } catch {
      setEventStatus('Failed to create event.');
    }
  };

  if (!email) {
    return (
      <div className="card">
        <h3>Email</h3>
        <p>Loading...</p>
        {status ? <p>{status}</p> : null}
      </div>
    );
  }

  return (
    <div className="card">
      <h3>{email.subject ?? '(No subject)'}</h3>
      <p>From: {email.from_email ?? 'Unknown sender'}</p>
      <div className="action-row">
        <button className="button" type="button" onClick={() => handleAction('ARCHIVE')}>
          Archive
        </button>
        <button className="button button-muted" type="button" onClick={() => handleAction('TRASH')}>
          Trash
        </button>
        <input
          type="datetime-local"
          value={snoozeUntil}
          onChange={(event) => setSnoozeUntil(event.target.value)}
        />
        <button className="button button-muted" type="button" onClick={handleSnooze}>
          Snooze
        </button>
        <button className="button" type="button" onClick={handleRunAutomation}>
          Run automation
        </button>
      </div>
      {email.importance_label ? (
        <div className="triage-panel">
          <p>Importance: {email.importance_label}</p>
          {email.why_important ? <p>{email.why_important}</p> : null}
          {email.summary_bullets.length > 0 ? (
            <ul>
              {email.summary_bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <button className="button" type="button" onClick={handleRunTriage}>
          Run triage
        </button>
      )}
      <p>{email.clean_body_text ?? ''}</p>
      <FeedbackControls emailId={email.id} />
      <div className="calendar-panel">
        <div className="calendar-header">
          <h4>Calendar</h4>
          <button className="button" type="button" onClick={handleProposeCalendar}>
            Propose times
          </button>
        </div>
        {calendarCandidates.length === 0 ? (
          <p>No calendar candidates yet.</p>
        ) : (
          calendarCandidates.map((candidate) => {
            const payload = candidate.payload ?? {};
            const title = typeof payload.title === 'string' ? payload.title : 'Untitled';
            const start = typeof payload.start === 'string' ? payload.start : '';
            const end = typeof payload.end === 'string' ? payload.end : '';
            const attendees = Array.isArray(payload.attendees) ? payload.attendees.join(', ') : '';
            return (
              <div key={candidate.id} className="calendar-row">
                <div>
                  <strong>{title}</strong>
                  <div>
                    {start ? new Date(start).toLocaleString() : 'Unknown start'} —{' '}
                    {end ? new Date(end).toLocaleString() : 'Unknown end'}
                  </div>
                  {attendees ? <div>Attendees: {attendees}</div> : null}
                </div>
                <button
                  className="button button-muted"
                  type="button"
                  onClick={() => handleCreateEvent(candidate)}
                >
                  Edit & create event
                </button>
              </div>
            );
          })
        )}
        {calendarStatus ? <p>{calendarStatus}</p> : null}
      </div>
      {activeCandidate ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modal-header">
              <h4>Create calendar event</h4>
              <button
                className="button button-muted"
                type="button"
                onClick={() => setActiveCandidate(null)}
              >
                Close
              </button>
            </div>
            <div className="modal-section">
              <h5>Suggested times</h5>
              {meetingSuggestions.length === 0 ? (
                <p>No suggestions yet.</p>
              ) : (
                <div className="suggestion-chips">
                  {meetingSuggestions.map((suggestion) => (
                    <button
                      key={`${suggestion.start}-${suggestion.end}`}
                      className="chip"
                      type="button"
                      onClick={() => handleSelectSuggestion(suggestion)}
                    >
                      {new Date(suggestion.start).toLocaleString()} —{' '}
                      {new Date(suggestion.end).toLocaleTimeString()}
                    </button>
                  ))}
                </div>
              )}
              {meetingStatus ? <p>{meetingStatus}</p> : null}
            </div>
            <div className="modal-section">
              <div className="form-row">
                <label htmlFor="event-title">Title</label>
                <input
                  id="event-title"
                  type="text"
                  value={eventForm.title}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, title: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-start">Start</label>
                <input
                  id="event-start"
                  type="datetime-local"
                  value={eventForm.start}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, start: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-end">End</label>
                <input
                  id="event-end"
                  type="datetime-local"
                  value={eventForm.end}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, end: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-timezone">Time zone</label>
                <input
                  id="event-timezone"
                  type="text"
                  value={eventForm.timezone}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, timezone: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-location">Location</label>
                <input
                  id="event-location"
                  type="text"
                  value={eventForm.location}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, location: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-attendees">Attendees (comma-separated)</label>
                <input
                  id="event-attendees"
                  type="text"
                  value={eventForm.attendees}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, attendees: event.target.value }))
                  }
                />
              </div>
              <div className="form-row">
                <label htmlFor="event-description">Description</label>
                <textarea
                  id="event-description"
                  rows={4}
                  value={eventForm.description}
                  onChange={(event) =>
                    setEventForm((prev) => ({ ...prev, description: event.target.value }))
                  }
                />
              </div>
              <div className="action-row">
                <button className="button" type="button" onClick={handleSubmitEvent}>
                  Create event
                </button>
                {eventLink ? (
                  <a
                    className="button button-muted"
                    href={eventLink}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open in Google Calendar
                  </a>
                ) : null}
              </div>
              {eventStatus ? <p>{eventStatus}</p> : null}
            </div>
          </div>
        </div>
      ) : null}
      <div className="draft-panel">
        <div className="draft-header">
          <h4>Draft reply</h4>
          <button className="button" type="button" onClick={handleProposeDraft}>
            {draft ? 'Regenerate draft' : 'Propose draft'}
          </button>
        </div>
        {draft ? (
          <div className="draft-form">
            <div className="form-row">
              <label htmlFor="draft-subject">Subject</label>
              <input
                id="draft-subject"
                type="text"
                value={draftSubject}
                onChange={(event) => setDraftSubject(event.target.value)}
              />
            </div>
            <div className="form-row">
              <label htmlFor="draft-body">Body</label>
              <textarea
                id="draft-body"
                rows={8}
                value={draftBody}
                onChange={(event) => setDraftBody(event.target.value)}
              />
            </div>
            <div className="action-row">
              <button className="button" type="button" onClick={handleCreateGmailDraft}>
                Create Gmail draft
              </button>
              {draft.gmail_draft_id ? (
                <a
                  className="button button-muted"
                  href={`https://mail.google.com/mail/u/0/#drafts?compose=${draft.gmail_draft_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open in Gmail
                </a>
              ) : null}
            </div>
          </div>
        ) : (
          <p>No draft yet.</p>
        )}
        {draftStatus ? <p>{draftStatus}</p> : null}
      </div>
      <div className="attachments">
        <div className="attachments-header">
          <h4>Attachments</h4>
          <button className="button" type="button" onClick={handleProcessAttachments}>
            Extract text
          </button>
        </div>
        {email.attachments.length === 0 ? (
          <p>No attachments found.</p>
        ) : (
          email.attachments.map((attachment: AttachmentSummary) => (
            <div key={attachment.id} className="attachment-row">
              <div>{attachment.filename ?? 'Untitled'}</div>
              <div>{attachment.mime_type ?? 'unknown'}</div>
              <div>{attachment.extraction_status ?? 'NOT_PROCESSED'}</div>
            </div>
          ))
        )}
      </div>
      {status ? <p>{status}</p> : null}
    </div>
  );
}
