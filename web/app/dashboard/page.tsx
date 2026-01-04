import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { getGoogleIntegrationStatusServer } from '../../lib/auth';
import { getEmailsServer } from '../../lib/emails';
import SyncNowButton from './sync-now-button';

export default async function DashboardPage() {
  let status;
  let emails = [];

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

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  return (
    <div className="card">
      <h3>Dashboard</h3>
      <SyncNowButton />
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
      <div className="inbox">
        {emails.length === 0 ? (
          <p>No messages found yet.</p>
        ) : (
          emails.map((email) => (
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
              <div className="email-snippet">{email.snippet ?? ''}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
