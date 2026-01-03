import type { ReactNode } from 'react';

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <section className="card">
      <header>
        <h2>Authenticated Layout</h2>
        <p>Navigation and account context will live here.</p>
      </header>
      <div>{children}</div>
    </section>
  );
}
