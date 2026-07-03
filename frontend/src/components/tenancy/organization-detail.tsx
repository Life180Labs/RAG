'use client';

import Link from 'next/link';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateWorkspaceForm } from '@/components/tenancy/create-workspace-form';
import { InviteMemberForm } from '@/components/tenancy/invite-member-form';
import { useOrganization, useWorkspaces } from '@/hooks/use-tenancy';

export function OrganizationDetail({ organizationId }: { organizationId: string }) {
  const {
    data: organization,
    isLoading: isOrgLoading,
    isError: isOrgError,
  } = useOrganization(organizationId);
  const {
    data: workspaces,
    isLoading: isWorkspacesLoading,
    isError: isWorkspacesError,
  } = useWorkspaces(organizationId);

  if (isOrgLoading) {
    return (
      <div className="w-full max-w-2xl space-y-3" data-testid="organization-detail-loading">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isOrgError || !organization) {
    return (
      <Alert variant="destructive" className="w-full max-w-2xl">
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
    <div className="w-full max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{organization.name}</h1>
          <p className="text-muted-foreground text-sm">/{organization.slug}</p>
        </div>
        <Badge variant={organization.status === 'active' ? 'default' : 'secondary'}>
          {organization.status}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invite a member</CardTitle>
        </CardHeader>
        <CardContent>
          <InviteMemberForm organizationId={organizationId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>New workspace</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateWorkspaceForm organizationId={organizationId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Workspaces</CardTitle>
        </CardHeader>
        <CardContent>
          {isWorkspacesLoading && (
            <div className="space-y-2" data-testid="workspaces-loading">
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {isWorkspacesError && (
            <Alert variant="destructive">
              <AlertTitle>Couldn&apos;t load workspaces</AlertTitle>
            </Alert>
          )}

          {workspaces && workspaces.length === 0 && (
            <p className="text-muted-foreground text-sm" data-testid="workspaces-empty">
              No workspaces yet. Create one above.
            </p>
          )}

          {workspaces && workspaces.length > 0 && (
            <ul className="divide-border divide-y" data-testid="workspaces-list">
              {workspaces.map((workspace) => (
                <li key={workspace.id} className="flex items-center justify-between py-3">
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspace.id}`}
                    className="font-medium hover:underline"
                  >
                    {workspace.name}
                  </Link>
                  <Badge variant={workspace.status === 'active' ? 'default' : 'secondary'}>
                    {workspace.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
