'use client';

import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { ChevronRight, Pencil, Plus } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateRepositoryForm } from '@/components/tenancy/create-repository-form';
import { useRepositories } from '@/hooks/use-repositories';
import { useProject } from '@/hooks/use-tenancy';
import { ApiRequestError } from '@/services/api-client';
import { updateProject } from '@/services/tenancy-service';

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  if (status === 'active') return 'default';
  if (status === 'archived') return 'outline';
  return 'secondary';
}

export function ProjectDashboard({
  organizationId,
  workspaceId,
  projectId,
}: {
  organizationId: string;
  workspaceId: string;
  projectId: string;
}) {
  const { data: project, isLoading, isError } = useProject(projectId);
  const {
    data: repositories,
    isLoading: isRepositoriesLoading,
    isError: isRepositoriesError,
  } = useRepositories(projectId);
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRename, setShowRename] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) {
    return (
      <div className="w-full max-w-3xl space-y-4" data-testid="project-dashboard-loading">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <Alert variant="destructive" className="w-full max-w-3xl">
        <AlertTitle>Couldn&apos;t load this project</AlertTitle>
        <AlertDescription>
          You may not have access, or it doesn&apos;t exist.{' '}
          <Link
            href={`/organizations/${organizationId}/workspaces/${workspaceId}`}
            className="underline"
          >
            Back to workspace
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  async function handleRename(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);
    try {
      await updateProject(projectId, { name: name || project!.name });
      await queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
      setSuccess(true);
      setShowRename(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to update project.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-foreground text-xl font-semibold">{project.name}</h1>
            <Badge variant={statusVariant(project.status)}>{project.status}</Badge>
          </div>
          <p className="text-muted-foreground mt-0.5 text-sm">/{project.slug}</p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={() => setShowRename((v) => !v)}
          >
            <Pencil className="h-3.5 w-3.5" />
            Rename
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setShowCreate((v) => !v)}>
            <Plus className="h-3.5 w-3.5" />
            New repository
          </Button>
        </div>
      </div>

      {success && (
        <Alert data-testid="project-update-success">
          <AlertTitle>Project renamed</AlertTitle>
        </Alert>
      )}

      {showRename && (
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Rename project</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="flex items-end gap-3" onSubmit={handleRename}>
              {error && (
                <Alert variant="destructive" className="basis-full">
                  <AlertTitle>Update failed</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="project-name">Name</Label>
                <Input
                  id="project-name"
                  placeholder={project.name}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving…' : 'Save'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {showCreate && (
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Create repository</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateRepositoryForm projectId={projectId} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
            Repositories
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isRepositoriesLoading && (
            <div className="space-y-px p-1" data-testid="repositories-loading">
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          )}

          {isRepositoriesError && (
            <div className="p-4">
              <Alert variant="destructive">
                <AlertTitle>Couldn&apos;t load repositories</AlertTitle>
              </Alert>
            </div>
          )}

          {repositories && repositories.length === 0 && (
            <div
              className="flex flex-col items-center justify-center py-10 text-center"
              data-testid="repositories-empty"
            >
              <p className="text-muted-foreground text-sm">No repositories yet.</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-3 gap-1.5"
                onClick={() => setShowCreate(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Create repository
              </Button>
            </div>
          )}

          {repositories && repositories.length > 0 && (
            <ul className="divide-border divide-y" data-testid="repositories-list">
              {repositories.map((repository) => (
                <li key={repository.id}>
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspaceId}/projects/${projectId}/repositories/${repository.id}`}
                    className="group hover:bg-muted/20 flex items-center justify-between px-5 py-3.5 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-foreground group-hover:text-primary truncate text-sm font-medium transition-colors">
                        {repository.name}
                      </p>
                      <p className="text-muted-foreground text-xs">/{repository.slug}</p>
                    </div>
                    <div className="ml-4 flex shrink-0 items-center gap-2">
                      <Badge variant={statusVariant(repository.status)}>{repository.status}</Badge>
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
