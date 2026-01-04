'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { Alert, markAlertRead } from '../../lib/alerts';

type AlertItemProps = {
  alert: Alert;
};

export default function AlertItem({ alert }: AlertItemProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleMarkRead = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await markAlertRead(alert.id);
      setStatus('Marked read.');
      router.refresh();
    } catch {
      setStatus('Failed to mark read.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="alert-row">
      <div>
        <div className="alert-title">
          {alert.email_subject ?? '(No subject)'}{' '}
          {alert.email_from ? <span className="alert-from">from {alert.email_from}</span> : null}
        </div>
        {alert.email_snippet ? <div className="alert-snippet">{alert.email_snippet}</div> : null}
        {alert.reason ? <div className="alert-reason">Reason: {alert.reason}</div> : null}
        {alert.email_internal_date_ts ? (
          <div className="alert-date">
            {new Date(alert.email_internal_date_ts).toLocaleString()}
          </div>
        ) : null}
        {status ? <div className="alert-status">{status}</div> : null}
      </div>
      <div className="alert-actions">
        <a className="button button-muted" href={`/dashboard/${alert.email_id}`}>
          View email
        </a>
        <button className="button" type="button" onClick={handleMarkRead} disabled={loading}>
          {loading ? 'Marking...' : 'Mark read'}
        </button>
      </div>
    </div>
  );
}
