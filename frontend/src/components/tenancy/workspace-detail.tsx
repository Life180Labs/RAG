'use client';

import Link from 'next/link';
import { ChevronRight, Plus } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateProjectForm } from '@/components/tenancy/create-project-form';
import { useProjects, useWorkspace } from '@/hooks/use-tenancy';

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  if (status === 'active') return 'default';
  if (status === 'archived') return 'outline';
  return 'secondary';
}

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
  const [showCreate, setShowCreate] = useState(false);

  if (isWorkspaceLoading) {
    return (
      <div className="w-full max-w-3xl space-y-4" data-testid="workspace-detail-loading">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <Alert variant="destructive" className="w-full max-w-3xl">
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
    <div className="w-full max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-foreground text-xl font-semibold">{workspace.name}</h1>
            <Badge variant={statusVariant(workspace.status)}>{workspace.status}</Badge>
          </div>
          <p className="text-muted-foreground mt-0.5 text-sm">/{workspace.slug}</p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={() => setShowCreate((v) => !v)}>
          <Plus className="h-3.5 w-3.5" />
          New project
        </Button>
      </div>

      {showCreate && (
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Create project</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateProjectForm workspaceId={workspaceId} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
            Projects
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isProjectsLoading && (
            <div className="space-y-px p-1" data-testid="projects-loading">
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          )}

          {isProjectsError && (
            <div className="p-4">
              <Alert variant="destructive">
                <AlertTitle>Couldn&apos;t load projects</AlertTitle>
              </Alert>
            </div>
          )}

          {projects && projects.length === 0 && (
            <div
              className="flex flex-col items-center justify-center py-10 text-center"
              data-testid="projects-empty"
            >
              <p className="text-muted-foreground text-sm">No projects yet.</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-3 gap-1.5"
                onClick={() => setShowCreate(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Create project
              </Button>
            </div>
          )}

          {projects && projects.length > 0 && (
            <ul className="divide-border divide-y" data-testid="projects-list">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspaceId}/projects/${project.id}`}
                    className="group hover:bg-muted/20 flex items-center justify-between px-5 py-3.5 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-foreground group-hover:text-primary truncate text-sm font-medium transition-colors">
                        {project.name}
                      </p>
                      <p className="text-muted-foreground text-xs">/{project.slug}</p>
                    </div>
                    <div className="ml-4 flex shrink-0 items-center gap-2">
                      <Badge variant={statusVariant(project.status)}>{project.status}</Badge>
                      <ChevronRight className="text-muted-foreground/50 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
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
