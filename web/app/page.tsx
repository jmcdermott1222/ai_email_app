import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="card">
      <h2>Welcome</h2>
      <p>
        This is the placeholder home page for the AI Email Copilot. Start by signing in with your
        Google account.
      </p>
      <p>
        <Link href="/login">Go to login</Link>
      </p>
    </div>
  );
}
