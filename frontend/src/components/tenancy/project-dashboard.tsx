'use client';

import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
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

  if (isLoading) {
    return (
      <div className="w-full max-w-2xl space-y-3" data-testid="project-dashboard-loading">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <Alert variant="destructive" className="w-full max-w-2xl">
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);
    try {
      await updateProject(projectId, { name: name || project!.name });
      await queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to update project.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{project.name}</h1>
          <p className="text-muted-foreground text-sm">/{project.slug}</p>
        </div>
        <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
          {project.status}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rename project</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
            {error && (
              <Alert variant="destructive" className="sm:basis-full">
                <AlertTitle>Update failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert data-testid="project-update-success" className="sm:basis-full">
                <AlertTitle>Project updated</AlertTitle>
              </Alert>
            )}
            <div className="flex-1 space-y-1">
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

      <Card>
        <CardHeader>
          <CardTitle>New repository</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateRepositoryForm projectId={projectId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Repositories</CardTitle>
        </CardHeader>
        <CardContent>
          {isRepositoriesLoading && (
            <div className="space-y-2" data-testid="repositories-loading">
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {isRepositoriesError && (
            <Alert variant="destructive">
              <AlertTitle>Couldn&apos;t load repositories</AlertTitle>
            </Alert>
          )}

          {repositories && repositories.length === 0 && (
            <p className="text-muted-foreground text-sm" data-testid="repositories-empty">
              No repositories yet. Create one above.
            </p>
          )}

          {repositories && repositories.length > 0 && (
            <ul className="divide-border divide-y" data-testid="repositories-list">
              {repositories.map((repository) => (
                <li key={repository.id} className="flex items-center justify-between py-3">
                  <Link
                    href={`/organizations/${organizationId}/workspaces/${workspaceId}/projects/${projectId}/repositories/${repository.id}`}
                    className="font-medium hover:underline"
                  >
                    {repository.name}
                  </Link>
                  <Badge variant={repository.status === 'active' ? 'default' : 'secondary'}>
                    {repository.status}
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
