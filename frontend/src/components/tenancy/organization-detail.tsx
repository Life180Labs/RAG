'use client';

import Link from 'next/link';
import { ChevronRight, Plus, UserPlus } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateWorkspaceForm } from '@/components/tenancy/create-workspace-form';
import { InviteMemberForm } from '@/components/tenancy/invite-member-form';
import { useOrganization, useWorkspaces } from '@/hooks/use-tenancy';

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  if (status === 'active') return 'default';
  if (status === 'archived') return 'outline';
  return 'secondary';
}

export function OrganizationDetail({ organizationId }: { organizationId: string }) {
  const { data: organization, isLoading: isOrgLoading, isError: isOrgError } = useOrganization(organizationId);
  const { data: workspaces, isLoading: isWorkspacesLoading, isError: isWorkspacesError } = useWorkspaces(organizationId);
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);
  const [showInvite, setShowInvite] = useState(false);

  if (isOrgLoading) {
    return (
      <div className="w-full max-w-3xl space-y-4" data-testid="organization-detail-loading">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isOrgError || !organization) {
    return (
      <Alert variant="destructive" className="w-full max-w-3xl">
        <AlertTitle>Couldn&apos;t load this organization</AlertTitle>
        <AlertDescription>
          You may not have access, or it doesn&apos;t exist.{' '}
          <Link href="/organizations" className="underline">
            Back to organizations
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-foreground">{organization.name}</h1>
            <Badge variant={statusVariant(organization.status)}>{organization.status}</Badge>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">/{organization.slug}</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setShowInvite((v) => !v)}>
            <UserPlus className="h-3.5 w-3.5" />
            Invite member
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setShowCreateWorkspace((v) => !v)}>
            <Plus className="h-3.5 w-3.5" />
            New workspace
          </Button>
        </div>
      </div>

      {showInvite && (
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Invite a member</CardTitle>
          </CardHeader>
          <CardContent>
            <InviteMemberForm organizationId={organizationId} />
          </CardContent>
        </Card>
      )}

      {showCreateWorkspace && (
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Create workspace</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateWorkspaceForm organizationId={organizationId} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Workspaces
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isWorkspacesLoading && (
            <div className="space-y-px p-1" data-testid="workspaces-loading">
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          )}

          {isWorkspacesError && (
            <div className="p-4">
              <Alert variant="destructive">
                <AlertTitle>Couldn&apos;t load workspaces</AlertTitle>
              </Alert>
            </div>
          )}

          {workspaces && workspaces.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 text-center" data-testid="workspaces-empty">
              <p className="text-sm text-muted-foreground">No workspaces yet.</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-3 gap-1.5"
                onClick={() => setShowCreateWorkspace(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Create workspace
              </Button>
            </div>
          )}

          {workspaces && workspaces.length > 0 && (
            <ul className="divide-y divide-border" data-testid="workspaces-list">
              {workspaces.map((workspace) => (
                <li key={workspace.id}>
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspace.id}`}
                    className="group flex items-center justify-between px-5 py-3.5 transition-colors hover:bg-muted/20"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                        {workspace.name}
                      </p>
                      <p className="text-xs text-muted-foreground">/{workspace.slug}</p>
                    </div>
                    <div className="ml-4 flex shrink-0 items-center gap-2">
                      <Badge variant={statusVariant(workspace.status)}>{workspace.status}</Badge>
                      <ChevronRight className="h-4 w-4 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
