'use client';

import Link from 'next/link';
import { useState } from 'react';
import { FileText, BarChart3, Settings, Boxes, Hash, Layers3, Search } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { DocumentList } from '@/components/documents/document-list';
import { DocumentUpload } from '@/components/documents/document-upload';
import { RepositorySettingsForm } from '@/components/tenancy/repository-settings-form';
import { useRepository, useRepositoryActivity } from '@/hooks/use-repositories';
import { cn } from '@/lib/utils';
import type { Repository } from '@/types/repository';

type Tab = 'overview' | 'documents' | 'settings';

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  if (status === 'active') return 'default';
  if (status === 'archived') return 'outline';
  return 'secondary';
}

function TabButton({
  label,
  icon,
  active,
  count,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  count?: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors -mb-px',
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground',
      )}
    >
      {icon}
      {label}
      {count !== undefined && (
        <span
          className={cn(
            'rounded-full px-1.5 py-0.5 text-[0.65rem] font-semibold tabular-nums',
            active ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground',
          )}
        >
          {count}
        </span>
      )}
    </button>
  );
}

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
}

function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <span className="text-muted-foreground/40">{icon}</span>
      </div>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">{value.toLocaleString()}</p>
    </div>
  );
}

function OverviewTab({ repository, activity, isActivityLoading }: {
  repository: Repository;
  activity: { action: string; created_at: string }[] | undefined;
  isActivityLoading: boolean;
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Documents" value={repository.document_count ?? 0} icon={<FileText className="h-4 w-4" />} />
        <StatCard label="Chunks" value={repository.chunk_count ?? 0} icon={<Hash className="h-4 w-4" />} />
        <StatCard label="Embeddings" value={repository.embedding_count ?? 0} icon={<Layers3 className="h-4 w-4" />} />
        <StatCard label="Retrievals" value={repository.retrieval_count ?? 0} icon={<Search className="h-4 w-4" />} />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isActivityLoading && (
            <div className="p-4">
              <Skeleton className="h-10 w-full" data-testid="repository-activity-loading" />
            </div>
          )}
          {activity && activity.length === 0 && (
            <p className="px-5 py-4 text-sm text-muted-foreground" data-testid="repository-activity-empty">
              No activity recorded yet.
            </p>
          )}
          {activity && activity.length > 0 && (
            <ul className="divide-y divide-border" data-testid="repository-activity-list">
              {activity.map((entry, index) => (
                <li key={index} className="flex items-center justify-between px-5 py-3">
                  <span className="text-sm text-foreground">{entry.action}</span>
                  <span className="text-xs text-muted-foreground">
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

function DocumentsTab({ repositoryId }: { repositoryId: string }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Upload documents</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentUpload repositoryId={repositoryId} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentList repositoryId={repositoryId} />
        </CardContent>
      </Card>
    </div>
  );
}

function SettingsTab({ repository }: { repository: Repository }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Pipeline defaults</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Default configuration applied when creating chunks, embeddings, and retrievals.
        </p>
      </CardHeader>
      <CardContent>
        <RepositorySettingsForm repository={repository} />
      </CardContent>
    </Card>
  );
}

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
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl space-y-4" data-testid="repository-dashboard-loading">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !repository) {
    return (
      <Alert variant="destructive" className="w-full max-w-4xl">
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
    <div className="w-full max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Boxes className="h-5 w-5 text-muted-foreground" />
            <h1 className="text-xl font-semibold text-foreground">{repository.name}</h1>
            <Badge variant={statusVariant(repository.status)}>{repository.status}</Badge>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">/{repository.slug}</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border" data-testid="repository-tabs">
        <TabButton
          label="Overview"
          icon={<BarChart3 className="h-3.5 w-3.5" />}
          active={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
        />
        <TabButton
          label="Documents"
          icon={<FileText className="h-3.5 w-3.5" />}
          active={activeTab === 'documents'}
          count={repository.document_count ?? 0}
          onClick={() => setActiveTab('documents')}
        />
        <TabButton
          label="Settings"
          icon={<Settings className="h-3.5 w-3.5" />}
          active={activeTab === 'settings'}
          onClick={() => setActiveTab('settings')}
        />
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <OverviewTab
          repository={repository}
          activity={activity}
          isActivityLoading={isActivityLoading}
        />
      )}
      {activeTab === 'documents' && <DocumentsTab repositoryId={repositoryId} />}
      {activeTab === 'settings' && <SettingsTab repository={repository} />}
    </div>
  );
}
