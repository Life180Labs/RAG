'use client';

import { Fragment } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

interface Breadcrumb {
  label: string;
  href: string;
}

function buildBreadcrumbs(pathname: string): Breadcrumb[] {
  const crumbs: Breadcrumb[] = [];

  if (pathname === '/' || pathname === '') return crumbs;

  const orgMatch = pathname.match(/\/organizations\/([^/]+)/);
  const wsMatch = pathname.match(/\/workspaces\/([^/]+)/);
  const projMatch = pathname.match(/\/projects\/([^/]+)/);
  const repoMatch = pathname.match(/\/repositories\/([^/]+)/);

  if (pathname === '/profile') {
    crumbs.push({ label: 'Profile', href: '/profile' });
    return crumbs;
  }

  if (pathname.startsWith('/organizations')) {
    crumbs.push({ label: 'Organizations', href: '/organizations' });
  }

  if (orgMatch) {
    const orgId = orgMatch[1];
    const orgHref = `/organizations/${orgId}`;
    crumbs.push({ label: 'Organization', href: orgHref });

    if (wsMatch) {
      const wsId = wsMatch[1];
      const wsHref = `${orgHref}/workspaces/${wsId}`;
      crumbs.push({ label: 'Workspace', href: wsHref });

      if (projMatch) {
        const projId = projMatch[1];
        const projHref = `${wsHref}/projects/${projId}`;
        crumbs.push({ label: 'Project', href: projHref });

        if (repoMatch) {
          const repoId = repoMatch[1];
          const repoHref = `${projHref}/repositories/${repoId}`;
          crumbs.push({ label: 'Repository', href: repoHref });
        }
      }
    }
  }

  return crumbs;
}

export function TopBar() {
  const pathname = usePathname();
  const breadcrumbs = buildBreadcrumbs(pathname);

  if (breadcrumbs.length === 0) return null;

  return (
    <header className="border-border bg-background/80 flex h-11 shrink-0 items-center border-b px-6 backdrop-blur-sm">
      <nav className="flex items-center gap-1.5 text-sm" aria-label="Breadcrumb">
        {breadcrumbs.map((crumb, i) => (
          <Fragment key={crumb.href}>
            {i > 0 && <ChevronRight className="text-muted-foreground/40 h-3.5 w-3.5 shrink-0" />}
            {i === breadcrumbs.length - 1 ? (
              <span className="text-foreground font-medium">{crumb.label}</span>
            ) : (
              <Link
                href={crumb.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </Fragment>
        ))}
      </nav>
    </header>
  );
}
