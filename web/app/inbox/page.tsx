import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { getGoogleIntegrationStatusServer } from '../../lib/auth';
import { getEmailsServer } from '../../lib/emails';
import { decodeHtmlEntities } from '../../lib/text';
import FeedbackControls from '../components/feedback-controls';
import SyncNowButton from '../dashboard/sync-now-button';

export default async function InboxPage() {
  try {
    await getGoogleIntegrationStatusServer();
  } catch (error) {
    const message = error instanceof Error ? error.message : '';
    if (message.includes('401')) {
      redirect('/login');
    }
    throw error;
  }

  const cookieHeader = cookies()
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join('; ');
  const emails = await getEmailsServer(cookieHeader);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Inbox</p>
          <h2 className="page-title">Your latest messages</h2>
          <p className="page-subtitle">Review, triage, and take action with confidence.</p>
        </div>
        <div className="page-actions">
          <SyncNowButton />
        </div>
      </header>
      <section className="card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Messages</h3>
            <p className="section-desc">Sync brings in the last 14 days from your inbox.</p>
          </div>
        </div>
        <div className="inbox">
          {emails.length === 0 ? (
            <p>No messages found yet.</p>
          ) : (
            emails.map((email) => {
              const gmailLink = email.gmail_message_id
                ? `https://mail.google.com/mail/u/0/#inbox/${email.gmail_message_id}`
                : null;
              return (
                <div key={email.id} className="email-row">
                  <div className="email-meta">
                    <span className="email-from">{email.from_email ?? 'Unknown sender'}</span>
                    <span className="email-date">
                      {email.internal_date_ts
                        ? new Date(email.internal_date_ts).toLocaleString()
                        : ''}
                    </span>
                  </div>
                  <a className="email-subject" href={`/dashboard/${email.id}`}>
                    {email.subject ?? '(No subject)'}
                  </a>
                  <div className="email-snippet">
                    {email.snippet ? decodeHtmlEntities(email.snippet) : ''}
                  </div>
                  {email.importance_label ? (
                    <div className="email-triage">
                      <span className="tag">{email.importance_label}</span>
                      {email.why_important ? <span>{email.why_important}</span> : null}
                    </div>
                  ) : null}
                  <div className="email-actions">
                    <a
                      className="button button-muted"
                      href={`/dashboard/${email.id}`}
                      title="Open email details"
                    >
                      View details
                    </a>
                    {gmailLink ? (
                      <a
                        className="button button-outline"
                        href={gmailLink}
                        target="_blank"
                        rel="noreferrer"
                        title="Open this message in Gmail"
                      >
                        View in Gmail
                      </a>
                    ) : null}
                  </div>
                  <FeedbackControls emailId={email.id} compact />
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
