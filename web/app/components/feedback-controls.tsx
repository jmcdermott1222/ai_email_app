'use client';

import { useState } from 'react';

import { apiFetch } from '../../lib/api';

type FeedbackLabel = 'IMPORTANT' | 'NOT_IMPORTANT' | 'SPAM' | 'NEWSLETTER_OK';

type FeedbackControlsProps = {
  emailId: number;
  compact?: boolean;
  onSubmitted?: () => void;
};

export default function FeedbackControls({
  emailId,
  compact = false,
  onSubmitted,
}: FeedbackControlsProps) {
  const [label, setLabel] = useState<FeedbackLabel>('NOT_IMPORTANT');
  const [reason, setReason] = useState('');
  const [alwaysIgnoreSender, setAlwaysIgnoreSender] = useState(false);
  const [alwaysIgnoreKeyword, setAlwaysIgnoreKeyword] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async () => {
    setStatus(null);
    try {
      await apiFetch(`/api/emails/${emailId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({
          feedback_label: label,
          reason: reason || null,
          always_ignore_sender: alwaysIgnoreSender,
          always_ignore_keyword: alwaysIgnoreKeyword || null,
        }),
      });
      setStatus('Saved.');
      onSubmitted?.();
    } catch {
      setStatus('Failed.');
    }
  };

  return (
    <div className={`feedback ${compact ? 'feedback-compact' : ''}`}>
      <div className="feedback-row">
        <label htmlFor={`feedback-label-${emailId}`}>Feedback</label>
        <select
          id={`feedback-label-${emailId}`}
          value={label}
          onChange={(event) => setLabel(event.target.value as FeedbackLabel)}
        >
          <option value="IMPORTANT">Important</option>
          <option value="NOT_IMPORTANT">Not important</option>
          <option value="SPAM">Spam</option>
          <option value="NEWSLETTER_OK">Newsletter ok</option>
        </select>
      </div>
      {!compact ? (
        <>
          <div className="feedback-row">
            <label htmlFor={`feedback-reason-${emailId}`}>Reason</label>
            <input
              id={`feedback-reason-${emailId}`}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Optional reason"
            />
          </div>
          <div className="feedback-row checkbox-row">
            <label htmlFor={`feedback-ignore-sender-${emailId}`}>
              Always ignore sender
            </label>
            <input
              id={`feedback-ignore-sender-${emailId}`}
              type="checkbox"
              checked={alwaysIgnoreSender}
              onChange={(event) => setAlwaysIgnoreSender(event.target.checked)}
            />
          </div>
          <div className="feedback-row">
            <label htmlFor={`feedback-ignore-keyword-${emailId}`}>
              Always ignore keyword
            </label>
            <input
              id={`feedback-ignore-keyword-${emailId}`}
              value={alwaysIgnoreKeyword}
              onChange={(event) => setAlwaysIgnoreKeyword(event.target.value)}
              placeholder="Optional keyword"
            />
          </div>
        </>
      ) : null}
      <div className="feedback-actions">
        <button className="button" type="button" onClick={handleSubmit}>
          Submit feedback
        </button>
        {status ? <span>{status}</span> : null}
      </div>
    </div>
  );
}
