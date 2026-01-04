import { redirect } from 'next/navigation';

import { getGoogleIntegrationStatusServer } from '../../lib/auth';

export default async function DashboardPage() {
  let status;

  try {
    status = await getGoogleIntegrationStatusServer();
  } catch (error) {
    const message = error instanceof Error ? error.message : '';
    if (message.includes('401')) {
      redirect('/login');
    }
    throw error;
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  return (
    <div className="card">
      <h3>Dashboard</h3>
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
    </div>
  );
}
