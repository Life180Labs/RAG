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
      <div className="bg-background flex min-h-screen flex-col items-center justify-center px-6 py-12">
        <div className="mb-10 flex flex-col items-center gap-3">
          <div className="bg-primary flex h-10 w-10 items-center justify-center rounded-xl">
            <Cpu className="text-primary-foreground h-5 w-5" />
          </div>
          <div className="text-center">
            <p className="text-foreground text-sm font-semibold">RAG Studio</p>
            <p className="text-muted-foreground text-xs">Enterprise Pipeline Platform</p>
          </div>
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="bg-background flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 scrollbar-thin overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
