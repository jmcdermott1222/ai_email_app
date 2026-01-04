import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { getGoogleIntegrationStatusServer } from '../../lib/auth';
import { getAlertsServer } from '../../lib/alerts';
import { DigestContent, getLatestDigestServer } from '../../lib/digests';
import { getEmailsServer } from '../../lib/emails';
import AlertItem from './alert-item';
import DigestRunButton from './digest-run-button';
import FeedbackControls from '../components/feedback-controls';
import SyncNowButton from './sync-now-button';

export default async function DashboardPage() {
  let status;
  let emails = [];
  let alerts = [];
  let digest = null;

  try {
    status = await getGoogleIntegrationStatusServer();
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
  emails = await getEmailsServer(cookieHeader);
  alerts = await getAlertsServer(cookieHeader);
  digest = await getLatestDigestServer(cookieHeader);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
  const digestContent = digest?.content_json as DigestContent | null;
  const sections = digestContent?.sections ?? null;

  return (
    <div className="card">
      <h3>Today</h3>
      <div className="today-actions">
        <SyncNowButton />
        <DigestRunButton />
      </div>
      {status.needs_reauth ? (
        <div className="banner">
          <p>Your Google connection needs reauthorization.</p>
          <a className="button" href={`${apiBaseUrl}/auth/google/start`}>
            Reconnect
          </a>
        </div>
      ) : null}
      <p>Connected: {status.connected ? 'Yes' : 'No'}</p>
      <p>Token status: {status.token_status ?? 'unknown'}</p>
      <div className="today-section">
        <h4>VIP alerts</h4>
        {alerts.length === 0 ? (
          <p>No VIP alerts right now.</p>
        ) : (
          <div className="alert-list">
            {alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>
      <div className="today-section">
        <h4>Daily digest</h4>
        {!digestContent || !sections ? (
          <p>No digest generated yet.</p>
        ) : (
          <div className="digest">
            <p className="digest-meta">
              Generated at {new Date(digestContent.generated_at).toLocaleString()} •{' '}
              {digestContent.counts?.needs_reply ?? 0} needs reply •{' '}
              {digestContent.counts?.important_fyi ?? 0} important FYI •{' '}
              {digestContent.counts?.newsletters ?? 0} newsletters
            </p>
            <div className="digest-section">
              <h5>Needs reply</h5>
              {sections.needs_reply.length === 0 ? (
                <p>No replies needed.</p>
              ) : (
                sections.needs_reply.map((item) => (
                  <div key={item.id} className="digest-row">
                    <a className="email-subject" href={`/dashboard/${item.id}`}>
                      {item.subject ?? '(No subject)'}
                    </a>
                    <div className="email-snippet">{item.snippet ?? ''}</div>
                  </div>
                ))
              )}
            </div>
            <div className="digest-section">
              <h5>Important FYI</h5>
              {sections.important_fyi.length === 0 ? (
                <p>No important FYI emails.</p>
              ) : (
                sections.important_fyi.map((item) => (
                  <div key={item.id} className="digest-row">
                    <a className="email-subject" href={`/dashboard/${item.id}`}>
                      {item.subject ?? '(No subject)'}
                    </a>
                    <div className="email-snippet">{item.snippet ?? ''}</div>
                  </div>
                ))
              )}
            </div>
            {sections.newsletters.length > 0 ? (
              <div className="digest-section">
                <h5>Newsletters</h5>
                {sections.newsletters.map((item) => (
                  <div key={item.id} className="digest-row">
                    <a className="email-subject" href={`/dashboard/${item.id}`}>
                      {item.subject ?? '(No subject)'}
                    </a>
                    <div className="email-snippet">{item.snippet ?? ''}</div>
                  </div>
                ))}
              </div>
            ) : null}
            <details className="digest-section">
              <summary>Everything else ({sections.everything_else.length})</summary>
              {sections.everything_else.length === 0 ? (
                <p>No additional messages.</p>
              ) : (
                sections.everything_else.map((item) => (
                  <div key={item.id} className="digest-row">
                    <a className="email-subject" href={`/dashboard/${item.id}`}>
                      {item.subject ?? '(No subject)'}
                    </a>
                    <div className="email-snippet">{item.snippet ?? ''}</div>
                  </div>
                ))
              )}
            </details>
          </div>
        )}
      </div>
      <div className="inbox">
        {emails.length === 0 ? (
          <p>No messages found yet.</p>
        ) : (
          emails.map((email) => (
            <div key={email.id} className="email-row">
              <div className="email-meta">
                <span className="email-from">{email.from_email ?? 'Unknown sender'}</span>
                <span className="email-date">
                  {email.internal_date_ts ? new Date(email.internal_date_ts).toLocaleString() : ''}
                </span>
              </div>
              <a className="email-subject" href={`/dashboard/${email.id}`}>
                {email.subject ?? '(No subject)'}
              </a>
              <div className="email-snippet">{email.snippet ?? ''}</div>
              {email.importance_label ? (
                <div className="email-triage">
                  <span>{email.importance_label}</span>
                  {email.why_important ? <span>{email.why_important}</span> : null}
                </div>
              ) : null}
              <FeedbackControls emailId={email.id} compact />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
