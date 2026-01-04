'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { apiFetch } from '../../lib/api';

export default function SyncNowButton() {
  const router = useRouter();
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSync = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await apiFetch('/api/sync/full', { method: 'POST' });
      setStatus('Sync complete.');
      router.refresh();
    } catch {
      setStatus('Sync failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sync-row">
      <button className="button" type="button" onClick={handleSync} disabled={loading}>
        {loading ? 'Syncing...' : 'Sync now'}
      </button>
      {status ? <span>{status}</span> : null}
    </div>
  );
}
