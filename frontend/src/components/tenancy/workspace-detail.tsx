'use client';

import Link from 'next/link';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateProjectForm } from '@/components/tenancy/create-project-form';
import { useProjects, useWorkspace } from '@/hooks/use-tenancy';

export function WorkspaceDetail({
  organizationId,
  workspaceId,
}: {
  organizationId: string;
  workspaceId: string;
}) {
  const {
    data: workspace,
    isLoading: isWorkspaceLoading,
    isError: isWorkspaceError,
  } = useWorkspace(workspaceId);
  const {
    data: projects,
    isLoading: isProjectsLoading,
    isError: isProjectsError,
  } = useProjects(workspaceId);

  if (isWorkspaceLoading) {
    return (
      <div className="w-full max-w-2xl space-y-3" data-testid="workspace-detail-loading">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <Alert variant="destructive" className="w-full max-w-2xl">
        <AlertTitle>Couldn&apos;t load this workspace</AlertTitle>
        <AlertDescription>
          You may not have access, or it doesn&apos;t exist.{' '}
          <Link href={`/organizations/${organizationId}`} className="underline">
            Back to organization
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{workspace.name}</h1>
          <p className="text-muted-foreground text-sm">/{workspace.slug}</p>
        </div>
        <Badge variant={workspace.status === 'active' ? 'default' : 'secondary'}>
          {workspace.status}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New project</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateProjectForm workspaceId={workspaceId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Projects</CardTitle>
        </CardHeader>
        <CardContent>
          {isProjectsLoading && (
            <div className="space-y-2" data-testid="projects-loading">
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {isProjectsError && (
            <Alert variant="destructive">
              <AlertTitle>Couldn&apos;t load projects</AlertTitle>
            </Alert>
          )}

          {projects && projects.length === 0 && (
            <p className="text-muted-foreground text-sm" data-testid="projects-empty">
              No projects yet. Create one above.
            </p>
          )}

          {projects && projects.length > 0 && (
            <ul className="divide-border divide-y" data-testid="projects-list">
              {projects.map((project) => (
                <li key={project.id} className="flex items-center justify-between py-3">
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspaceId}/projects/${project.id}`}
                    className="font-medium hover:underline"
                  >
                    {project.name}
                  </Link>
                  <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
                    {project.status}
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
