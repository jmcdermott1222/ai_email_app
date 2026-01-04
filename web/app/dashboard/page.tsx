import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { getGoogleIntegrationStatusServer } from '../../lib/auth';
import { getAlertsServer } from '../../lib/alerts';
import { DigestContent, getLatestDigestServer } from '../../lib/digests';
import { decodeHtmlEntities } from '../../lib/text';
import AlertItem from './alert-item';
import DigestRunButton from './digest-run-button';
import SyncNowButton from './sync-now-button';

export default async function DashboardPage() {
  let status;
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
  alerts = await getAlertsServer(cookieHeader, false);
  digest = await getLatestDigestServer(cookieHeader);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
  const digestContent = digest?.content_json as DigestContent | null;
  const sections = digestContent?.sections ?? null;
  const digestVipSenders = Array.isArray(digestContent?.vip_senders)
    ? digestContent?.vip_senders
    : null;
  const fallbackVipSenders = alerts
    .map((alert) => alert.email_from)
    .filter((value) => value) as string[];
  const vipSenders = Array.from(new Set(digestVipSenders ?? fallbackVipSenders));
  const unreadAlerts = alerts.filter((alert) => !alert.read_at);
  const vipSenderText = vipSenders.length
    ? vipSenders.slice(0, 3).join(', ') +
      (vipSenders.length > 3 ? ` +${vipSenders.length - 3} more` : '')
    : 'your VIP list';
  const vipCount =
    typeof digestContent?.vip_count === 'number' ? digestContent.vip_count : alerts.length;
  const needsReplyCount = digestContent?.counts?.needs_reply ?? 0;
  const importantCount = digestContent?.counts?.important_fyi ?? 0;
  const newsletterCount = digestContent?.counts?.newsletters ?? 0;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Today</p>
          <h2 className="page-title">What you need to see</h2>
        </div>
        <div className="status-stack">
          <span className={`status-chip ${status.connected ? 'ok' : 'warn'}`}>
            {status.connected ? 'Connected' : 'Not connected'}
          </span>
          <span className="status-chip">Token: {status.token_status ?? 'unknown'}</span>
        </div>
      </header>
      <div className="page-actions">
        <SyncNowButton />
        <DigestRunButton />
      </div>
      {status.needs_reauth ? (
        <div className="banner banner-warning">
          <p>Your Google connection needs reauthorization.</p>
          <a
            className="button"
            href={`${apiBaseUrl}/auth/google/start`}
            title="Reconnect Google to restore access"
          >
            Reconnect
          </a>
        </div>
      ) : null}
      <div className="stack">
        <section className="card card-tinted">
          <div className="section-header">
            <div>
              <h3 className="section-title">Daily digest</h3>
              <p className="section-desc">A quick scan of what needs your attention.</p>
            </div>
          </div>
          {!digestContent || !sections ? (
            <p>No digest generated yet.</p>
          ) : (
            <div className="digest">
              <div className="digest-summary card-sub">
                <p className="eyebrow">Overview</p>
                <p>You&apos;ve received</p>
                <ul className="digest-list">
                  <li>
                    {vipCount} VIP {vipCount === 1 ? 'email' : 'emails'} from {vipSenderText}
                  </li>
                  <li>{needsReplyCount} emails that need responses</li>
                  <li>{importantCount} important FYIs</li>
                  <li>{newsletterCount} newsletters</li>
                </ul>
              </div>
              <details className="digest-section" open>
                <summary>VIP alerts ({unreadAlerts.length})</summary>
                {unreadAlerts.length === 0 ? (
                  <p>No VIP alerts right now.</p>
                ) : (
                  <div className="alert-list">
                    {unreadAlerts.map((alert) => (
                      <AlertItem key={alert.id} alert={alert} />
                    ))}
                  </div>
                )}
              </details>
              <p className="digest-meta">
                Generated at {new Date(digestContent.generated_at).toLocaleString()} •{' '}
                {needsReplyCount} needs reply • {importantCount} important FYI • {newsletterCount}{' '}
                newsletters
              </p>
              <details className="digest-section" open>
                <summary>Needs reply ({sections.needs_reply.length})</summary>
                {sections.needs_reply.length === 0 ? (
                  <p>No replies needed.</p>
                ) : (
                  sections.needs_reply.map((item) => (
                    <div key={item.id} className="digest-row">
                      <a className="email-subject" href={`/dashboard/${item.id}`}>
                        {item.subject ?? '(No subject)'}
                      </a>
                      <div className="email-snippet">{decodeHtmlEntities(item.snippet)}</div>
                    </div>
                  ))
                )}
              </details>
              <details className="digest-section" open>
                <summary>Important FYI ({sections.important_fyi.length})</summary>
                {sections.important_fyi.length === 0 ? (
                  <p>No important FYI emails.</p>
                ) : (
                  sections.important_fyi.map((item) => (
                    <div key={item.id} className="digest-row">
                      <a className="email-subject" href={`/dashboard/${item.id}`}>
                        {item.subject ?? '(No subject)'}
                      </a>
                      <div className="email-snippet">{decodeHtmlEntities(item.snippet)}</div>
                    </div>
                  ))
                )}
              </details>
              <details className="digest-section">
                <summary>Newsletters ({sections.newsletters.length})</summary>
                {sections.newsletters.length === 0 ? (
                  <p>No newsletters today.</p>
                ) : (
                  sections.newsletters.map((item) => (
                    <div key={item.id} className="digest-row">
                      <a className="email-subject" href={`/dashboard/${item.id}`}>
                        {item.subject ?? '(No subject)'}
                      </a>
                      <div className="email-snippet">{decodeHtmlEntities(item.snippet)}</div>
                    </div>
                  ))
                )}
              </details>
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
                      <div className="email-snippet">{decodeHtmlEntities(item.snippet)}</div>
                    </div>
                  ))
                )}
              </details>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
