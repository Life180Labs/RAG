import { AuthGuard } from '@/components/auth-guard';
import { RepositoryDashboard } from '@/components/tenancy/repository-dashboard';

export default async function RepositoryDashboardPage({
  params,
}: {
  params: Promise<{
    organizationId: string;
    workspaceId: string;
    projectId: string;
    repositoryId: string;
  }>;
}) {
  const { organizationId, workspaceId, projectId, repositoryId } = await params;

  return (
    <AuthGuard>
      <RepositoryDashboard
        organizationId={organizationId}
        workspaceId={workspaceId}
        projectId={projectId}
        repositoryId={repositoryId}
      />
    </AuthGuard>
  );
}
