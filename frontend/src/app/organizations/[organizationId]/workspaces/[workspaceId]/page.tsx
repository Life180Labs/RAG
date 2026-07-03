import { AuthGuard } from '@/components/auth-guard';
import { WorkspaceDetail } from '@/components/tenancy/workspace-detail';

export default async function WorkspaceDetailPage({
  params,
}: {
  params: Promise<{ organizationId: string; workspaceId: string }>;
}) {
  const { organizationId, workspaceId } = await params;

  return (
    <main className="flex flex-1 justify-center p-8">
      <AuthGuard>
        <WorkspaceDetail organizationId={organizationId} workspaceId={workspaceId} />
      </AuthGuard>
    </main>
  );
}
