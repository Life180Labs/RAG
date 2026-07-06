'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Building2,
  ChevronRight,
  Cpu,
  Database,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Settings,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { useAuth } from '@/providers/auth-provider';
import { useHealth } from '@/hooks/use-health';

interface RouteContext {
  orgId?: string;
  workspaceId?: string;
  projectId?: string;
  repositoryId?: string;
}

function parseRoute(pathname: string): RouteContext {
  const ctx: RouteContext = {};
  const orgMatch = pathname.match(/\/organizations\/([^/]+)/);
  const wsMatch = pathname.match(/\/workspaces\/([^/]+)/);
  const projMatch = pathname.match(/\/projects\/([^/]+)/);
  const repoMatch = pathname.match(/\/repositories\/([^/]+)/);
  if (orgMatch) ctx.orgId = orgMatch[1];
  if (wsMatch) ctx.workspaceId = wsMatch[1];
  if (projMatch) ctx.projectId = projMatch[1];
  if (repoMatch) ctx.repositoryId = repoMatch[1];
  return ctx;
}

function NavItem({
  href,
  label,
  icon,
  active,
  indent = false,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  indent?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        'group flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm transition-colors',
        indent && 'ml-3 pl-2.5',
        active
          ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
          : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/40 hover:text-sidebar-foreground',
      )}
    >
      <span
        className={cn(
          'transition-colors',
          active
            ? 'text-sidebar-primary'
            : 'text-sidebar-foreground/40 group-hover:text-sidebar-foreground/70',
        )}
      >
        {icon}
      </span>
      {label}
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sidebar-foreground/30 mt-4 mb-1 px-3 text-[0.65rem] font-semibold tracking-widest uppercase">
      {children}
    </p>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const { data: health } = useHealth();
  const route = parseRoute(pathname);

  const { orgId, workspaceId, projectId, repositoryId } = route;

  const orgBase = orgId ? `/organizations/${orgId}` : null;
  const wsBase = orgBase && workspaceId ? `${orgBase}/workspaces/${workspaceId}` : null;
  const projBase = wsBase && projectId ? `${wsBase}/projects/${projectId}` : null;
  const repoBase = projBase && repositoryId ? `${projBase}/repositories/${repositoryId}` : null;

  const isHealthy = health?.status === 'healthy';

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : (user?.email?.slice(0, 2).toUpperCase() ?? '?');

  return (
    <aside className="border-sidebar-border bg-sidebar flex h-full w-[220px] shrink-0 flex-col border-r">
      {/* Brand */}
      <div className="border-sidebar-border flex h-12 shrink-0 items-center border-b px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="bg-primary flex h-6 w-6 items-center justify-center rounded-md">
            <Cpu className="text-primary-foreground h-3.5 w-3.5" />
          </div>
          <span className="text-sidebar-foreground text-[0.8rem] font-semibold tracking-tight">
            RAG Studio
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 scrollbar-thin flex-col overflow-y-auto p-3">
        <NavItem
          href="/"
          label="Overview"
          icon={<BarChart3 className="h-4 w-4" />}
          active={pathname === '/'}
        />

        {!isLoading && isAuthenticated && (
          <>
            <NavItem
              href="/organizations"
              label="Organizations"
              icon={<Building2 className="h-4 w-4" />}
              active={pathname === '/organizations'}
            />

            {orgId && orgBase && (
              <>
                <SectionLabel>Context</SectionLabel>
                <NavItem
                  href={orgBase}
                  label="Organization"
                  icon={<Building2 className="h-3.5 w-3.5" />}
                  active={pathname === orgBase}
                  indent
                />
                <NavItem
                  href={`${orgBase}/settings`}
                  label="Settings"
                  icon={<Settings className="h-3.5 w-3.5" />}
                  active={pathname === `${orgBase}/settings`}
                  indent
                />
                {workspaceId && wsBase && (
                  <NavItem
                    href={wsBase}
                    label="Workspace"
                    icon={<FolderKanban className="h-3.5 w-3.5" />}
                    active={!projectId && pathname.startsWith(wsBase)}
                    indent
                  />
                )}
                {projectId && projBase && (
                  <NavItem
                    href={projBase}
                    label="Project"
                    icon={<LayoutDashboard className="h-3.5 w-3.5" />}
                    active={!repositoryId && pathname.startsWith(projBase)}
                    indent
                  />
                )}
              </>
            )}

            {repositoryId && repoBase && (
              <>
                <SectionLabel>Repository</SectionLabel>
                <NavItem
                  href={repoBase}
                  label="Repository"
                  icon={<Database className="h-3.5 w-3.5" />}
                  active={pathname.startsWith(repoBase)}
                  indent
                />
              </>
            )}
          </>
        )}
      </nav>

      {/* Bottom: health + user */}
      <div className="border-sidebar-border shrink-0 space-y-3 border-t p-3">
        <div className="flex items-center gap-2 px-1">
          <span
            className={cn('h-1.5 w-1.5 rounded-full', isHealthy ? 'bg-green-400' : 'bg-red-400')}
          />
          <span className="text-sidebar-foreground/40 text-[0.7rem]">
            {isHealthy ? 'API online' : health ? 'API degraded' : 'Checking…'}
          </span>
        </div>

        {!isLoading && isAuthenticated && user && (
          <div className="border-sidebar-border bg-sidebar-accent/20 rounded-md border p-2">
            <div className="flex items-center gap-2">
              <div className="bg-primary/20 text-primary flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[0.6rem] font-semibold">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sidebar-foreground truncate text-[0.7rem] font-medium">
                  {user.full_name || user.email}
                </p>
                <p className="text-sidebar-foreground/40 truncate text-[0.65rem]">{user.role}</p>
              </div>
            </div>
            <button
              onClick={() => logout()}
              className="text-sidebar-foreground/50 hover:bg-sidebar-accent/40 hover:text-sidebar-foreground mt-2 flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-[0.7rem] transition-colors"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
          </div>
        )}

        {!isLoading && !isAuthenticated && (
          <Link
            href="/login"
            className="border-sidebar-border text-sidebar-foreground/60 hover:bg-sidebar-accent/40 hover:text-sidebar-foreground flex w-full items-center justify-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition-colors"
          >
            Sign in
            <ChevronRight className="h-3 w-3" />
          </Link>
        )}
      </div>
    </aside>
  );
}
