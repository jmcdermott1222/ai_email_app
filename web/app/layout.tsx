import './globals.css';

import type { ReactNode } from 'react';
import { Fraunces, Manrope } from 'next/font/google';

import AppHeader from './components/app-header';

const manrope = Manrope({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

export const metadata = {
  title: 'Clearview Email',
  description: 'The emails you need to see and nothing else.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${fraunces.variable}`}>
        <div className="app-shell">
          <AppHeader />
          <main className="app-main">
            <div className="container">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
