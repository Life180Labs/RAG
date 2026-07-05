'use client';

import { usePathname } from 'next/navigation';
import { Cpu } from 'lucide-react';

import { Sidebar } from './sidebar';
import { TopBar } from './top-bar';

const AUTH_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));

  if (isAuthRoute) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-12">
        <div className="mb-10 flex flex-col items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
            <Cpu className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-foreground">RAG Studio</p>
            <p className="text-xs text-muted-foreground">Enterprise Pipeline Platform</p>
          </div>
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="scrollbar-thin flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
