export default function LoginPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  return (
    <div className="page">
      <div className="auth-shell">
        <div className="card auth-card">
          <p className="eyebrow">Secure sign-in</p>
          <h2>Connect your Google account</h2>
          <p className="section-desc">
            We use OAuth to connect to Gmail and Calendar. Drafts are created in Gmail, never sent
            automatically.
          </p>
          <a
            className="button"
            href={`${apiBaseUrl}/auth/google/start`}
            title="Start the secure Google OAuth flow"
          >
            Connect Google
          </a>
        </div>
        <div className="card soft">
          <h3>What you get</h3>
          <ul>
            <li>Daily digest and VIP alerts.</li>
            <li>Meeting time suggestions.</li>
            <li>Draft replies in your voice.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
