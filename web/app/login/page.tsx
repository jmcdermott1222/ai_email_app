export default function LoginPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  return (
    <div className="card">
      <h2>Login</h2>
      <p>Connect your Google account to continue.</p>
      <a className="button" href={`${apiBaseUrl}/auth/google/start`}>
        Connect Google
      </a>
    </div>
  );
}
