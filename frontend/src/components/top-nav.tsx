'use client';

import Link from 'next/link';

import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAuth } from '@/providers/auth-provider';

export function TopNav() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <nav className="flex justify-end gap-2 p-4">
      {!isLoading && isAuthenticated && (
        <Link
          href="/organizations"
          className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }))}
        >
          Organizations
        </Link>
      )}
      {!isLoading && (
        <Link
          href={isAuthenticated ? '/profile' : '/login'}
          className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
        >
          {isAuthenticated ? 'Profile' : 'Sign in'}
        </Link>
      )}
    </nav>
  );
}
