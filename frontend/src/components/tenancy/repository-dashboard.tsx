'use client';

import Link from 'next/link';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { DocumentList } from '@/components/documents/document-list';
import { DocumentUpload } from '@/components/documents/document-upload';
import { RepositorySettingsForm } from '@/components/tenancy/repository-settings-form';
import { useRepository, useRepositoryActivity } from '@/hooks/use-repositories';
import type { Repository } from '@/types/repository';

const STAT_LABELS: { key: keyof Repository; label: string }[] = [
  { key: 'document_count', label: 'Documents' },
  { key: 'chunk_count', label: 'Chunks' },
  { key: 'embedding_count', label: 'Embeddings' },
  { key: 'retrieval_count', label: 'Retrievals' },
];

export function RepositoryDashboard({
  organizationId,
  workspaceId,
  projectId,
  repositoryId,
}: {
  organizationId: string;
  workspaceId: string;
  projectId: string;
  repositoryId: string;
}) {
  const { data: repository, isLoading, isError } = useRepository(repositoryId);
  const { data: activity, isLoading: isActivityLoading } = useRepositoryActivity(repositoryId);

  if (isLoading) {
    return (
      <div className="w-full max-w-2xl space-y-3" data-testid="repository-dashboard-loading">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError || !repository) {
    return (
      <Alert variant="destructive" className="w-full max-w-2xl">
        <AlertTitle>Couldn&apos;t load this repository</AlertTitle>
        <AlertDescription>
          You may not have access, or it doesn&apos;t exist.{' '}
          <Link
            href={`/organizations/${organizationId}/workspaces/${workspaceId}/projects/${projectId}`}
            className="underline"
          >
            Back to project
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{repository.name}</h1>
          <p className="text-muted-foreground text-sm">/{repository.slug}</p>
        </div>
        <Badge variant={repository.status === 'active' ? 'default' : 'secondary'}>
          {repository.status}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4" data-testid="repository-stats">
            {STAT_LABELS.map(({ key, label }) => (
              <div key={key}>
                <dt className="text-muted-foreground text-xs">{label}</dt>
                <dd className="text-lg font-semibold">{repository[key]}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <DocumentUpload repositoryId={repositoryId} />
          <DocumentList repositoryId={repositoryId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <RepositorySettingsForm repository={repository} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {isActivityLoading && (
            <Skeleton className="h-10 w-full" data-testid="repository-activity-loading" />
          )}

          {activity && activity.length === 0 && (
            <p className="text-muted-foreground text-sm" data-testid="repository-activity-empty">
              No activity recorded yet.
            </p>
          )}

          {activity && activity.length > 0 && (
            <ul className="divide-border divide-y text-sm" data-testid="repository-activity-list">
              {activity.map((entry, index) => (
                <li key={index} className="flex items-center justify-between py-2">
                  <span>{entry.action}</span>
                  <span className="text-muted-foreground">
                    {new Date(entry.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
