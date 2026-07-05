import { AuthGuard } from '@/components/auth-guard';
import { ProjectDashboard } from '@/components/tenancy/project-dashboard';

export default async function ProjectDashboardPage({
  params,
}: {
  params: Promise<{ organizationId: string; workspaceId: string; projectId: string }>;
}) {
  const { organizationId, workspaceId, projectId } = await params;

  return (
    <AuthGuard>
      <ProjectDashboard
        organizationId={organizationId}
        workspaceId={workspaceId}
        projectId={projectId}
      />
    </AuthGuard>
  );
}
