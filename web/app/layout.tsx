import './globals.css';

import type { ReactNode } from 'react';

export const metadata = {
  title: 'AI Email Copilot',
  description: 'Private email + calendar copilot',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <h1>AI Email Copilot</h1>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
