'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { runDigestNow } from '../../lib/digests';

export default function DigestRunButton() {
  const router = useRouter();
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await runDigestNow();
      setStatus('Digest updated.');
      router.refresh();
    } catch {
      setStatus('Digest failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sync-row">
      <button className="button" type="button" onClick={handleRun} disabled={loading}>
        {loading ? 'Generating...' : 'Run digest now'}
      </button>
      {status ? <span>{status}</span> : null}
    </div>
  );
}
