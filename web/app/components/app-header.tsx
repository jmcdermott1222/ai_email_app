'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { apiFetch } from '../../lib/api';

type NavItem = {
  label: string;
  href: string;
  isActive: (path: string) => boolean;
};

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Today',
    href: '/dashboard',
    isActive: (path) => path.startsWith('/dashboard'),
  },
  {
    label: 'Inbox',
    href: '/inbox',
    isActive: (path) => path.startsWith('/inbox'),
  },
  {
    label: 'Settings',
    href: '/settings',
    isActive: (path) => path.startsWith('/settings'),
  },
];

export default function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [logoutStatus, setLogoutStatus] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  const handleLogout = async () => {
    setIsLoggingOut(true);
    setLogoutStatus(null);
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
      setLogoutStatus('Signed out.');
      router.push('/login');
      router.refresh();
    } catch {
      setLogoutStatus('Sign-out failed.');
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <header className="app-header">
      <div className="header-inner">
        <Link className="brand" href="/dashboard">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-text">
            <span className="brand-title">Clearview Email</span>
            <span className="brand-subtitle">The emails you need to see and nothing else</span>
          </span>
        </Link>
        <nav className="nav">
          {NAV_ITEMS.map((item) => {
            const isActive = item.isActive(pathname);
            return (
              <Link
                key={item.label}
                className={`nav-link ${isActive ? 'nav-link-active' : ''}`}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                title={`Go to ${item.label}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="nav-actions">
          <a
            className="button button-outline"
            href={`${apiBaseUrl}/auth/google/start`}
            title="Connect or reconnect your Google account"
          >
            Connect Google
          </a>
          <button
            className="button button-muted"
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            title="Sign out of the app"
          >
            {isLoggingOut ? 'Signing out...' : 'Log out'}
          </button>
          {logoutStatus ? <span className="status-text">{logoutStatus}</span> : null}
        </div>
      </div>
    </header>
  );
}
