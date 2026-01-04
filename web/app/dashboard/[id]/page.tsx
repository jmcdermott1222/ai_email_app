'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { apiFetch } from '../../../lib/api';
import { AttachmentSummary, EmailDetail } from '../../../lib/emails';
import FeedbackControls from '../../components/feedback-controls';

export default function EmailDetailPage() {
  const params = useParams();
  const router = useRouter();
  const emailId = Number(params.id);
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [snoozeUntil, setSnoozeUntil] = useState('');

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
