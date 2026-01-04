'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { apiFetch } from '../../../lib/api';
import { AttachmentSummary, EmailDetail } from '../../../lib/emails';

export default function EmailDetailPage() {
  const params = useParams();
  const router = useRouter();
  const emailId = Number(params.id);
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);

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
      <p>{email.clean_body_text ?? ''}</p>
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
